from flask import Flask, request, session
from collections import OrderedDict
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import os
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = os.urandom(24)
 
# Directory to save images
IMAGE_DIR = 'patient_images'
os.makedirs(IMAGE_DIR, exist_ok=True)

# Database setup
conn = sqlite3.connect('nutrition_clinic.db', check_same_thread=False)
cursor = conn.cursor()

# Create a table for storing patient data
cursor.execute('''CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    age INTEGER,
                    height REAL,
                    weight REAL,
                    health_status TEXT,
                    allergies TEXT,
                    food_preferences TEXT,
                    blood_group TEXT,
                    vitamin_deficiency TEXT,
                    exercise_days INTEGER,
                    exercise_duration INTEGER,
                    goal TEXT,
                    front_image TEXT,
                    side_image TEXT,
                    back_image TEXT
                )''')
conn.commit()

# Step by step conversation in English and Arabic
conversation_steps = {
    "en": [
        "Please enter your full name:",
        "How old are you?",
        "What is your height (in cm)?",
        "What is your weight (in kg)?",
        "Do you have any health conditions?",
        "Do you have any food allergies?",
        "Are there any foods you dislike or prefer?",
        "What is your blood group?",
        "Do you have any vitamin deficiencies?",
        "How many days a week do you exercise?",
        "How long is each exercise session (in minutes)?",
        "What is your goal?",
        "Please send a picture of your body (front view).",
        "Please send a picture of your body (side view).",
        "Please send a picture of your body (back view)."
    ],
    "ar": [
        "الرجاء إدخال اسمك الكامل:",
        "كم عمرك؟",
        "ما هو طولك (بالسنتيمتر)؟",
        "ما هو وزنك (بالكيلوجرام)؟",
        "هل لديك أي حالات صحية؟",
        "هل لديك أي حساسية غذائية؟",
        "هل هناك أطعمة لا تحبها أو تفضلها؟",
        "ما هي فصيلة دمك؟",
        "هل لديك أي نقص في الفيتامينات؟",
        "كم يومًا في الأسبوع تمارس الرياضة؟",
        "كم تستغرق كل جلسة رياضية (بالدقائق)؟",
        "ما هو هدفك؟",
        "يرجى إرسال صورة لجسمك (من الأمام).",
        "يرجى إرسال صورة لجسمك (من الجانب).",
        "يرجى إرسال صورة لجسمك (من الخلف)."
    ]
}
session = {}
@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    incoming_msg = request.values.get('Body', '').lower()
    from_number = request.values.get('From', '')

    if 'patient_data' not in session:
        session['patient_data'] = {}
    if from_number not in session['patient_data']:
        session['patient_data'][from_number] = {"step": 0, "lang": "en"}

    patient_data = session['patient_data'][from_number]
    step = patient_data["step"]

    try:
        if step == 0:
            if incoming_msg in ["arabic", "english"]:
                patient_data["lang"] = "ar" if incoming_msg == "arabic" else "en"
                response = conversation_steps[patient_data["lang"]][step]
                patient_data["step"] += 1
            else:
                response = "👋 Welcome to the Nutrition Clinic!\n\n Please choose your preferred language (Arabic/English):"
        else:
            lang = patient_data["lang"]
            if step < len(conversation_steps[lang]):
                if step == 1 and not incoming_msg.isalpha():
                    response = f"Invalid input for {conversation_steps[lang][step-1]}. Please try again."
                else:
                    response = conversation_steps[lang][step]
                    patient_data["step"] += 1

                # Capture patient information based on the step
                if step == 1:
                    patient_data["name"] = incoming_msg
                elif step == 2:
                    patient_data["age"] = int(incoming_msg)
                elif step == 3:
                    patient_data["height"] = float(incoming_msg)
                elif step == 4:
                    patient_data["weight"] = float(incoming_msg)
                elif step == 5:
                    patient_data["health_status"] = incoming_msg
                elif step == 6:
                    patient_data["allergies"] = incoming_msg
                elif step == 7:
                    patient_data["food_preferences"] = incoming_msg
                elif step == 8:
                    patient_data["blood_group"] = incoming_msg
                elif step == 9:
                    patient_data["vitamin_deficiency"] = incoming_msg
                elif step == 10:
                    patient_data["exercise_days"] = int(incoming_msg)
                elif step == 11:
                    patient_data["exercise_duration"] = int(incoming_msg)
                elif step == 12:
                    patient_data["goal"] = incoming_msg
                elif step == 13:
                    # Save the front view image
                    front_image_path = save_image(request.values.get('MediaUrl0', ''), from_number, 'front')
                    patient_data["front_image"] = front_image_path
                elif step == 14:
                    # Save the side view image
                    side_image_path = save_image(request.values.get('MediaUrl0', ''), from_number, 'side')
                    patient_data["side_image"] = side_image_path
                elif step == 15:
                    # Save the back view image
                    back_image_path = save_image(request.values.get('MediaUrl0', ''), from_number, 'back')
                    patient_data["back_image"] = back_image_path

                if step == len(conversation_steps[lang]):
                    save_patient_data(from_number)
                    response = "Thank you! Your information has been recorded."
                    session['patient_data'].pop(from_number, None)

            else:
                response = "Thank you! Your information has been recorded."

    except ValueError:
        patient_data["step"] -= 1
        response = f"Invalid input for {conversation_steps[lang][step-1]}. Please try again."

    session.modified = True

    resp = MessagingResponse()
    resp.message(response)
    return str(resp)

def save_image(image_url, phone_number, view):
    if not image_url:
        return None
    # Use Twilio's Media URL to download the image
    response = requests.get(image_url)
    image_bytes = response.content
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    image_filename = f"{phone_number}_{timestamp}_{view}.jpg"
    image_path = os.path.join(IMAGE_DIR, image_filename)
    with open(image_path, 'wb') as image_file:
        image_file.write(image_bytes)
    return image_path

def save_patient_data(phone_number):
    patient_data = session['patient_data'][phone_number]
    cursor.execute('''INSERT INTO patients (name, age, height, weight, health_status, allergies, food_preferences, 
                                            blood_group, vitamin_deficiency, exercise_days, exercise_duration, goal, front_image, side_image, back_image)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                   (patient_data.get("name"), patient_data.get("age"), patient_data.get("height"), patient_data.get("weight"), patient_data.get("health_status"), patient_data.get("allergies"),
                    patient_data.get("food_preferences"), patient_data.get("blood_group"), patient_data.get("vitamin_deficiency"), patient_data.get("exercise_days"), 
                    patient_data.get("exercise_duration"), patient_data.get("goal"), patient_data.get("front_image"), patient_data.get("side_image"), patient_data.get("back_image")))
    conn.commit()

if __name__ == '__main__':
    if not os.path.exists('images'):
        os.makedirs('images')
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)    

  
