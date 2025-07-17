#!/usr/bin/env python
"""
Convert JPEG image to ICO format with multiple resolutions.
"""
import os
from PIL import Image

def convert_to_ico(input_path, output_path, sizes=(16, 32, 48, 256)):
    """
    Convert an image to ICO format with multiple resolutions.
    
    Args:
        input_path (str): Path to the input image
        output_path (str): Path where the ICO file will be saved
        sizes (tuple): Sizes (in pixels) to include in the ICO file
    """
    # Open the original image
    img = Image.open(input_path)
    
    # Create a list to store the different size images
    img_list = []
    
    # Resize the image to the required sizes
    for size in sizes:
        resized_img = img.copy()
        resized_img.thumbnail((size, size), Image.Resampling.LANCZOS)
        img_list.append(resized_img)
    
    # Create the directory for the output file if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save the resized images as an ICO file
    img_list[0].save(
        output_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in img_list],
        append_images=img_list[1:]
    )
    
    print(f"Converted {input_path} to {output_path} with sizes {sizes}px")

if __name__ == "__main__":
    input_file = r"C:\Users\Work\Desktop\Brocus CLI\icon\Icon for Brocus cli app.jpg"
    output_file = r"C:\Users\Work\Desktop\Brocus CLI\icon\Icon for Brocus cli app.ico"
    
    convert_to_ico(input_file, output_file)

