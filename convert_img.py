import base64
from PIL import Image
from io import BytesIO

# Use the correct path
image_path = r"D:/Work/Autonomous_Hacks_Finale/garbage_pile.png"

# Read and validate the image first
try:
    with Image.open(image_path) as img:
        print(f"✓ Image loaded successfully: {img.format} {img.size}")
        
        # Convert to RGB if needed (remove transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        
        # Save to bytes and encode
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        encoded = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
        data_url = f"data:image/png;base64,{encoded}"
        
        print(f"✓ Base64 encoded successfully: {len(encoded)} characters")
        print(f"\nBase64 string (first 100 chars):\n{encoded[:100]}...")
        print(f"\nFull data URL:\n{data_url}")
        
except Exception as e:
    print(f"✗ Error: {e}")