from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from pdf2image import convert_from_bytes
import os
import uuid
import boto3
from db import database  # ✅ Import database from db.py
from models import products, orders
from dotenv import load_dotenv
from sqlalchemy import select, update, delete


# ✅ Load Environment Variables
load_dotenv()

app = FastAPI()

# ✅ Connect to Database
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# ✅ AWS S3 Configuration
AWS_ACCESS_KEY_ID = "ASIAXVH2SGC63C6L7GGD"
AWS_SECRET_ACCESS_KEY = "tdPCSuC/SJYRunkRE1OFF4TYi+mQrblEVBGF3AhN"
AWS_S3_BUCKET_NAME = "scalablebucket1"
AWS_REGION = "us-east-1"
AWS_SESSION_TOKEN = "IQoJb3JpZ2luX2VjEG4aCXVzLXdlc3QtMiJIMEYCIQDJ9VMZ/FWBRFe2rtzKtsL6e1vdXICkGBPGvcErBOCpXAIhAPkV4jZ/0uQIciVA3bveQL2wYiLPn9b88dk9tNRj4svoKr0CCMf//////////wEQABoMNTI2NjU4OTczODg1IgxtyPIrjVNt3qOu6QcqkQK/WjzutDYWd090JXFqkFOPEmbFQXQzmJXsMbGF8MWrZwcIz5T5pLHoW3r5dCxP979H5DnImT7NCmi9B8YNtXQPOirGq1OTN6cUYNSrozX46pxQ7wACX1doWrC+SrVjfXUhjuFY97jIR7k/1X5FWaYlsyS1XgrK3SRJZ7I6Am5Xx3gaqyn2w9QAQu3+FXeX9yEYoPQb/wd3+t7aAdTW49KL6LN+j4ax91a3wJ/NHwPC/digUhUqNTm2D8JRpVg9EKwkpt+8h9/z+51JawyAeZfy5tFD0MQ8At1tCUo2es2Q/ihKUlNQouDkOJTeVXgR1fMrjYtRxmF94wLeZUwmZU7AWue+8vsa0JcZyNvCMvkXO8UwmNn8vgY6nAGxRJPaMfN0kORGAZbPERubrvlVWsfDUokM/K9ppThUMtpfnqcOxt0k8KJa7/teLUq7oI/E8BmlRiIN+rBaDntCrEk5TrfKBt05XTNtqkvBz2lABMtDUypol8X0KxATlQi8ccYaUdvNotXUTxEhdcbtIfJXSb341bfqX34k+sRWlADWan3/nc3XYySAEpcgjFfDXDaAfE9Pnm+jT5I="

if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET_NAME]):
    raise RuntimeError("AWS credentials or bucket name are missing! Check your .env file.")

# ✅ Poppler Path (PDF to Image Converter)
POPPLER_PATH = r"C:\poppler\Library\bin"  # Windows Example
IMAGE_DIR = "static/images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# ✅ Serve Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ Initialize S3 Client
s3_client = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN
)

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI on AWS!"}

@app.post("/products/")
async def create_product(
    name, 
    description, 
    price, 
    file: UploadFile = File(...)
):
    try:
        # ✅ Convert PDF to Image
        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Invalid PDF file uploaded.")

        images = convert_from_bytes(pdf_bytes, poppler_path=POPPLER_PATH) if POPPLER_PATH else convert_from_bytes(pdf_bytes)
        if not images:
            raise HTTPException(status_code=500, detail="PDF conversion failed.")

        # ✅ Upload First Page of PDF as Product Image
        image_filename = f"{uuid.uuid4()}_page1.png"
        temp_image_path = os.path.join(IMAGE_DIR, image_filename)
        images[0].save(temp_image_path, format="PNG")

        s3_key = f"product_images/{image_filename}"
        s3_client.upload_file(temp_image_path, AWS_S3_BUCKET_NAME, s3_key, ExtraArgs={"ContentType": "image/png"})

        image_url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

        # ✅ Store Product in Database with Image URL
        query = products.insert().values(name=name, description=description, price=price, image=image_url)
        await database.execute(query)

        # ✅ Delete Temporary Image
        os.remove(temp_image_path)

        return {"message": "Product created successfully"}

    except HTTPException as he:
        return {"error": he.detail}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

@app.get("/products/")
async def get_products():
    query = select(products)  # ✅ Correct way to select all columns from the table
    result = await database.fetch_all(query)  # ✅ Execute query in FastAPI
    return {"products": result} if result else {"message": "No products found"}



### **📌 Update (Edit) Product API**
@app.put("/products/{product_id}")
async def update_product(
    product_id: int,
    name: str,
    description: str,
    price: float,
    file: UploadFile = File(None)
):
    try:
        # ✅ Check if the product exists
        product_query = select(products).where(products.c.id == product_id)
        existing_product = await database.fetch_one(product_query)

        if not existing_product:
            raise HTTPException(status_code=404, detail="Product not found")

        # ✅ Update fields dynamically
        update_values = {}
        if name: update_values["name"] = name
        if description: update_values["description"] = description
        if price: update_values["price"] = price

        # ✅ Handle new image upload if provided
        if file:
            pdf_bytes = await file.read()
            images = convert_from_bytes(pdf_bytes, poppler_path=POPPLER_PATH) if POPPLER_PATH else convert_from_bytes(pdf_bytes)
            if not images:
                raise HTTPException(status_code=500, detail="PDF conversion failed.")

            image_filename = f"{uuid.uuid4()}_page1.png"
            temp_image_path = os.path.join(IMAGE_DIR, image_filename)
            images[0].save(temp_image_path, format="PNG")

            s3_key = f"product_images/{image_filename}"
            s3_client.upload_file(temp_image_path, AWS_S3_BUCKET_NAME, s3_key, ExtraArgs={"ContentType": "image/png"})
            image_url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

            update_values["image"] = image_url
            os.remove(temp_image_path)

        # ✅ Update Product in Database
        update_query = update(products).where(products.c.id == product_id).values(update_values)
        await database.execute(update_query)

        return {"message": "Product updated successfully", "updated_fields": update_values}

    except HTTPException as he:
        return {"error": he.detail}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


### **📌 Delete Product API**
@app.delete("/products/{product_id}")
async def delete_product(product_id: int):
    try:
        # ✅ Check if product exists
        product_query = select(products).where(products.c.id == product_id)
        existing_product = await database.fetch_one(product_query)

        if not existing_product:
            raise HTTPException(status_code=404, detail="Product not found")

        # ✅ Delete from database
        delete_query = delete(products).where(products.c.id == product_id)
        await database.execute(delete_query)

        return {"message": "Product deleted successfully"}

    except HTTPException as he:
        return {"error": he.detail}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

@app.post("/convert-pdf/")
async def convert_pdf(file: UploadFile = File(...)):
    try:
        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Invalid PDF file uploaded.")

        images = convert_from_bytes(pdf_bytes, poppler_path=POPPLER_PATH) if POPPLER_PATH else convert_from_bytes(pdf_bytes)
        if not images:
            raise HTTPException(status_code=500, detail="PDF conversion failed.")

        image_urls = []
        for i, image in enumerate(images):
            image_filename = f"{uuid.uuid4()}_page{i+1}.png"
            temp_image_path = os.path.join(IMAGE_DIR, image_filename)

            image.save(temp_image_path, format="PNG")

            if not os.path.exists(temp_image_path):
                raise FileNotFoundError(f"File not found: {temp_image_path}")

            s3_key = f"pdf_images/{image_filename}"
            s3_client.upload_file(temp_image_path, AWS_S3_BUCKET_NAME, s3_key, ExtraArgs={"ContentType": "image/png"})

            image_url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
            image_urls.append(image_url)

            os.remove(temp_image_path)

        return {"filename": file.filename, "image_urls": image_urls, "message": "PDF converted and uploaded to S3 successfully."}

    except HTTPException as he:
        return {"error": he.detail}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
    

@app.post("/orders/")
async def create_order(
    product_id,
    quantity,
    customer_name
):
    try:
        # ✅ Check if product exists
        product_query = select(products).where(products.c.id == product_id)
        product = await database.fetch_one(product_query)

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # ✅ Insert order into the database
        order_query = orders.insert().values(
            product_id=product_id,
            quantity=quantity,
            customer_name=customer_name
        )
        order_id = await database.execute(order_query)

        return {
            "message": "Order created successfully",
            "order": {
                "order_id": order_id,
                "product_id": product_id,
                "quantity": quantity,
                "customer_name": customer_name
            }
        }

    except HTTPException as he:
        return {"error": he.detail}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

# ✅ Get All Orders
@app.get("/orders/")
async def get_orders():
    query = select(orders)
    result = await database.fetch_all(query)
    return {"orders": result} if result else {"message": "No orders found"}

# ✅ Get a Single Order by ID
@app.get("/orders/{order_id}")
async def get_order(order_id: int):
    query = select(orders).where(orders.c.id == order_id)
    order = await database.fetch_one(query)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {"order": order}
