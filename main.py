from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")
flask_secret_key = os.getenv("FLASK_SECRET_KEY")

genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")


app = Flask(__name__)
app.config["SECRET_KEY"] = flask_secret_key
socketio = SocketIO(app)



rooms = {}

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        if code not in rooms:
            break
    
    return code



@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
            name = request.form.get("name")
            code = request.form.get("code")
            join = request.form.get("join", False)
            create = request.form.get("create", False)

            if not name:
                return render_template("home.html", error="Please enter a name.", code=code, name=name)
    
            if join != False and not code:
                return render_template("home.html", error="Please enter a a room code.", code=code, name=name)

            room = code
            if create != False:
                room = generate_unique_code(4)
                rooms[room] = {"members": 0, "messages": []}
            elif code not in rooms:
                return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
            session["room"] = room
            session["name"] = name

            return redirect(url_for("room"))
 
    return render_template("home.html")


@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    
    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return

    content = {
        "name" : session.get("name", "AI_CHATBOT"),
        "message" : data["data"]
    }

    #This is where AI comes in
    print("type(content[message]): ", type(content["message"]))
    

    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")


    filler_content = {
        "name" : "AI_CHATBOT",
        "message" : "thinking..."
    }

    send(filler_content, to=room)
    rooms[room]["messages"].append(filler_content)
    print(f"AI_CHATBOT said: {filler_content["message"]}")


    response = model.generate_content(content["message"])


    ai_content = {
        "name" : "AI_CHATBOT",
        "message" : response.text.replace('\n', '<br>')
    }
    send(ai_content, to=room)
    rooms[room]["messages"].append(ai_content)
    print(f"AI_CHATBOT said: {ai_content["message"]}")

    


@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name":name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}") 

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    

    #THIS PERMANENTLY DELETES ROOM, SO HAVE AI JOIN THE ROOM WITH THE USER SO IT NEVER HITS THIS LINE OF CODE
    leave_room(room)
    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

if __name__ == "__main__":
    socketio.run(app, debug=True)