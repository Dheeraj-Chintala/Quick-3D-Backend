from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import uuid
import os
import numpy as np
from PIL import Image
from stl import mesh
import numpy as np
from PIL import Image
import trimesh
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload/")
async def upload(file: UploadFile = File(...), height: float = Form(5.0)):
    temp_image_path = f"temp_{uuid.uuid4().hex}.png"
    with open(temp_image_path, "wb") as f:
        f.write(await file.read())

    image = Image.open(temp_image_path)

    stl_filename = f"{uuid.uuid4().hex}.stl"
    image_to_stl(image, stl_filename, height=height)

    os.remove(temp_image_path)

    return JSONResponse(content={"filename": stl_filename})
@app.delete("/delete-stl/")
async def delete_stl(filename: str = Query(...)):

    safe_path = os.path.join(".", os.path.basename(filename))

    if os.path.exists(safe_path):
        os.remove(safe_path)
        return {"message": f"{filename} deleted successfully."}
    else:
        raise HTTPException(status_code=404, detail="File not found.")

@app.get("/download-stl/")
async def download_stl(filename: str = Query(...)):
    return FileResponse(filename, media_type="application/sla", filename=filename)


def image_to_stl(image: Image.Image, output_path: str, height: float = 5.0):
  
    image = image.convert("RGBA")
    data = np.array(image)

    alpha = data[:, :, 3]
    visible_mask = alpha > 10

    gray = np.dot(data[:, :, :3], [0.299, 0.587, 0.114])
    gray[~visible_mask] = 0

    gray_normalized = (gray / 255.0) * height
    gray_normalized[visible_mask] += 5.0

    MAX_SIZE = 256
    if image.width > MAX_SIZE or image.height > MAX_SIZE:
        image.thumbnail((MAX_SIZE, MAX_SIZE))

    width, height_img = image.size
    data = np.array(image)

    alpha = data[:, :, 3]
    visible_mask = alpha > 10 


    gray = np.dot(data[:, :, :3], [0.299, 0.587, 0.114])
    gray[~visible_mask] = 0

    gray_normalized = (gray / 255.0) * height

    vertices = []
    faces = []

    for y in range(height_img - 1):
        for x in range(width - 1):
            z00 = gray_normalized[y, x]
            z01 = gray_normalized[y, x + 1]
            z10 = gray_normalized[y + 1, x]
            z11 = gray_normalized[y + 1, x + 1]

            if visible_mask[y, x] or visible_mask[y, x + 1] or visible_mask[y + 1, x] or visible_mask[y + 1, x + 1]:
                i = len(vertices)
                vertices += [
                    [x, y, z00],       # v0
                    [x + 1, y, z01],   # v1
                    [x, y + 1, z10],   # v2
                    [x + 1, y + 1, z11]  # v3
                ]
                faces += [
                    [i, i + 1, i + 2],
                    [i + 1, i + 3, i + 2]
                ]

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    mesh.export(output_path)
