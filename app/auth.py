from flask import Blueprint, request, jsonify

app_auth = Blueprint('app_auth', __name__)

# Mock user database
users = {}

@app_auth.route('/register', methods=['POST'])
def register():
    username = request.json.get('username')
    password = request.json.get('password')
    if username in users:
        return jsonify({'message': 'User already exists!'}), 400
    users[username] = password
    return jsonify({'message': 'User registered successfully!'}), 201

@app_auth.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    if users.get(username) != password:
        return jsonify({'message': 'Invalid credentials!'}), 401
    return jsonify({'message': 'Login successful!'}), 200

@app_auth.route('/logout', methods=['POST'])
def logout():
    # Logic for logout (e.g., removing session data) would go here
    return jsonify({'message': 'Logout successful!'}), 200