from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer
from PIL import Image
import os
import json

# Load model and tokenizer
model = VisionEncoderDecoderModel.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
processor = ViTImageProcessor.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
tokenizer = AutoTokenizer.from_pretrained("nlpconnect/vit-gpt2-image-captioning")

# Caption generation function (fixed: beam search disabled)
def generate_caption(image_path):
    image = Image.open(image_path).convert("RGB")
    pixel_values = processor(images=image, return_tensors="pt").pixel_values
    output_ids = model.generate(pixel_values, max_length=16, num_beams=1)  # beam search disabled
    caption = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    return caption.strip()

# Directory containing images
image_dir = "output/images"
captions = {}

# Process all images in the directory
for filename in os.listdir(image_dir):
    if filename.lower().endswith((".png", ".jpg", ".jpeg")):
        path = os.path.join(image_dir, filename)
        print(f"🔍 Generating caption for: {filename}")
        captions[filename] = generate_caption(path)

# Save captions to JSON
output_path = "output/image_captions.json"
with open(output_path, "w") as f:
    json.dump(captions, f, indent=2)

print(f"✅ Captions saved to {output_path}")
