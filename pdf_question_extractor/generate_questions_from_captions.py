import json

with open("output/image_captions.json") as f:
    captions = json.load(f)

questions = []

for filename, caption in captions.items():
    question = {
        "question": f"What does this image likely represent?",
        "options": [
            {"label": "A", "text": caption, "image": None},
            {"label": "B", "text": "A random object", "image": None},
            {"label": "C", "text": "An unrelated thing", "image": None},
            {"label": "D", "text": "None of the above", "image": None}
        ],
        "answer": "A",
        "images": f"output/images/{filename}"
    }
    questions.append(question)

with open("output/generated_questions.json", "w", encoding="utf-8") as f:
    json.dump(questions, f, indent=2, ensure_ascii=False)

print("✅ Questions saved to: output/generated_questions.json")
