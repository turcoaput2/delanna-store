from flask import Blueprint, request, jsonify

# Create a blueprint for order management
orders_bp = Blueprint('orders', __name__)

# In-memory storage for orders (for example purposes)
orders = []

@orders_bp.route('/orders', methods=['GET'])
def get_orders():
    return jsonify(orders), 200

@orders_bp.route('/orders', methods=['POST'])
def create_order():
    order_data = request.json
    orders.append(order_data)
    return jsonify(order_data), 201

@orders_bp.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    if 0 <= order_id < len(orders):
        return jsonify(orders[order_id]), 200
    return jsonify({'error': 'Order not found'}), 404

@orders_bp.route('/orders/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    if 0 <= order_id < len(orders):
        order_data = request.json
        orders[order_id] = order_data
        return jsonify(order_data), 200
    return jsonify({'error': 'Order not found'}), 404

@orders_bp.route('/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    if 0 <= order_id < len(orders):
        orders.pop(order_id)
        return jsonify({'message': 'Order deleted'}), 200
    return jsonify({'error': 'Order not found'}), 404

