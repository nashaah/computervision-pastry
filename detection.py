## UI library import

import tkinter as tk
from tkinter import ttk
import mysql.connector
from roboflow import Roboflow
import supervision as sv
import cv2
import datetime

# Define variables globally
tree = None
order_saved_window = None

# Function to fetch product prices from MySQL database
def fetch_prices(products_dict):
    # Connect to MySQL database
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="donutsdb"
    )
    cursor = connection.cursor()

    # Fetch prices for products
    for product in products_dict.keys():
        cursor.execute("SELECT price FROM product WHERE product_name = %s", (product,))
        row = cursor.fetchone()
        if row:
            products_dict[product] = (products_dict[product], row[0])
        else:
            products_dict[product] = (products_dict[product], "N/A")

    # Close database connection
    cursor.close()
    connection.close()

def update_detection(products_dict):
    global tree  # Access the globally defined tree
    # Clear previous content
    for widget in products_frame.winfo_children():
        widget.destroy()
    if len(products_dict) == 0:
        label = tk.Label(products_frame, text="No products detected", background="#F7EADB", font=("Helvetica", 18))
        label.pack()
    else:
        detected_label = tk.Label(products_frame, text="Detected Products", background="#F7EADB", font=("Helvetica", 18))
        detected_label.pack()
        # Configure styling for table
        style = ttk.Style()
        style.configure("Treeview", background="#F7EADB")
        tree = ttk.Treeview(products_frame, columns=("Product", "Quantity", "Price"), show="headings")
        tree.heading("Product", text="Product")
        tree.heading("Quantity", text="Quantity")
        tree.heading("Price", text="Price")
        total_price = 0  # Initialize total price variable
        for element, data in products_dict.items():
            quantity, price = data
            tree.insert("", "end", values=(element, quantity, price*quantity))
            total_price += price
        tree.pack(fill="both", expand=True)
        # Add label for total price
        total_label = tk.Label(products_frame, text=f"Grand Total: {total_price}", background="#F7EADB", font=("Helvetica",14))
        total_label.pack()
        next_label = tk.Label(products_frame, text="Press N to continue", background="#F7EADB", font=("Helvetica",12))
        next_label.pack()
        root.bind('n',save_order_and_close)

def save_order_and_close(event=None):
    global tree, order_saved_window  # Access the globally defined tree & order_saved_window
    if tree is not None:
        total_qty = sum(int(tree.item(item, "values")[1]) for item in tree.get_children())
        total_price = sum(float(tree.item(item, "values")[2]) for item in tree.get_children())
    
        # Connect to MySQL database
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="donutsdb"
        )
        cursor = connection.cursor()

        try:
            # Insert record into detect_orders table
            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO detect_orders (orderdate, totalprice, totalqty) VALUES (%s, %s, %s)",
                           (current_date, total_price, total_qty))
            connection.commit()
            
            # Get the auto-incremented primary key (detect_orders_id) of the inserted record
            detect_orders_id = cursor.lastrowid
            
            for item in tree.get_children():
                product_name = tree.item(item, "values")[0]
                quantity = int(tree.item(item, "values")[1])
                price = float(tree.item(item, "values")[2])
                
                
                # Retrieve product_id based on product_name
                cursor.execute("SELECT productid FROM product WHERE product_name = %s", (product_name,))
                row = cursor.fetchone()
                if row:
                    product_id = row[0]
                else:
                    # Handle the case if product_id is not found
                    product_id = None
                
                # Insert record into detect_orderdetail table
                cursor.execute("INSERT INTO detect_orderdetail (detect_order_id, productid, qty, price) VALUES (%s, %s, %s, %s)", (detect_orders_id, product_id, quantity, price))
                connection.commit()
                
            # Show success message
            order_saved_window = tk.Toplevel(root)
            order_saved_window.title("Confirm Order")
            order_saved_label = tk.Label(order_saved_window, text="Confirm Your Order", font=("Helvetica", 18), background="#F7EADB")
            order_saved_label.pack()
            
            cursor.execute("SELECT * FROM detect_orders ORDER BY orderdate DESC LIMIT 1")
            order_data = cursor.fetchone()
            if order_data:
                order_id, order_date, order_total_price, order_total_qty = order_data
                order_details_frame = tk.Frame(order_saved_window)
                order_details_frame.pack(pady=10)
                order_details_label = tk.Label(order_details_frame, text="Most Recent Order:", font=("Helvetica", 14), background="#F7EADB")
                order_details_label.pack()
                order_table = ttk.Treeview(order_details_frame, columns=("Product", "Quantity", "Price"), show="headings")
                order_table.heading("Product", text="Product")
                order_table.heading("Quantity", text="Quantity")
                order_table.heading("Price", text="Price")
                
                cursor.execute("SELECT product.product_name, detect_orderdetail.qty, detect_orderdetail.price FROM detect_orderdetail JOIN product ON detect_orderdetail.productid = product.productid WHERE detect_orderdetail.detect_order_id = %s", (order_id,))
                order_items = cursor.fetchall()
                for item in order_items:
                    order_table.insert("", "end", values=item)
                order_table.pack()
                
                confirm_button = tk.Button(order_saved_window, text="Confirm Order", command=lambda: confirm_order(detect_orders_id))
                confirm_button.pack()

            root.withdraw()
            video_capture.release()
            cv2.destroyAllWindows()
            
        except Exception as e:
            print("An error occurred:", e)
            connection.rollback()
        finally:
            cursor.close()
            connection.close()
            
def confirm_order(detect_orders_id):
    try:
        
        connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="donutsdb"
        )
        cursor = connection.cursor()
        cursor.execute("INSERT INTO orders (orderdate, totalprice, totalqty) SELECT orderdate, totalprice, totalqty FROM detect_orders WHERE detect_orders_id=%s",(detect_orders_id,))
        connection.commit()
        
        order_id = cursor.lastrowid
        cursor.execute("INSERT INTO orderdetail (orderid, productid, qty, price) SELECT %s, productid, qty, price FROM detect_orderdetail WHERE detect_order_id = %s", (order_id, detect_orders_id))
        connection.commit()
        
        print("Order confirmed and transferred successfully!")
        
    except Exception as e:
        print("An error has occured in the transfer of orders: ", e)
        connection.rollback()
        
## Function to run AI detection model
def process_frame():
    ## Reads the frames from the webcam by CV2
    ret, frame = video_capture.read()
    ## Generate results as JSON file based on Roboflow model
    result = model.predict(frame, confidence=40, overlap=30).json()
    ## Iterate the number of items in the result based on the model's predictions
    labels = [item["class"] for item in result["predictions"]]
    detections = sv.Detections.from_roboflow(result)
    ## Puts boxes & labels around the detected objects
    annotated_image = bounding_box_annotator.annotate(scene=frame, detections=detections)
    annotated_image = label_annotator.annotate(scene=annotated_image, detections=detections, labels=labels)
    ## Prints the boxes & labels on the webcam view
    cv2.imshow('Video', annotated_image)
    # Update products dictionary
    products_dict = {}
    for product in labels:
        if product in products_dict:
            products_dict[product] += 1
        else:
            products_dict[product] = 1
    fetch_prices(products_dict)
    update_detection(products_dict)
    ## Exit the program by pressing 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        root.quit()
    else:
        root.after(10, process_frame)

root = tk.Tk()
root.title("Detect Products")
root.configure(bg="#F7EADB")

products_frame = tk.Frame(root)
products_frame.pack(side=tk.LEFT, padx=20, pady=20)

## Imports the Roboflow model project

rf = Roboflow(api_key="Hu8D7dVZ8JfYjC7qIlwP")
project = rf.workspace().project("abad-2024")
model = project.version(13).model

## Variables for labelling
label_annotator = sv.LabelAnnotator()
bounding_box_annotator = sv.BoxAnnotator()

## Webcam
video_capture = cv2.VideoCapture(0)

process_frame()

root.mainloop()

video_capture.release()
cv2.destroyAllWindows()
