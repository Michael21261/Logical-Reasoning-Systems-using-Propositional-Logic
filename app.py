from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from sympy import symbols, SympifyError, sympify
from sympy.logic.boolalg import And, Or, Not, Implies, Equivalent
from sympy.logic.inference import satisfiable, valid
from collections import OrderedDict
import uuid
import re


from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key_here' 


users = {}


OPERATORS = {
    '∧': And,
    '∨': Or,
    '¬': Not,
    '→': Implies,
    '↔': Equivalent
}



def parse_statement(statement_str):
    potential_symbols = set(re.findall(r'[A-Za-z][A-Za-z0-9]*', statement_str))
    symbol_map = {s: symbols(s) for s in potential_symbols}
    processed_statement_str = statement_str
    processed_statement_str = processed_statement_str.replace('∧', '&')
    processed_statement_str = processed_statement_str.replace('∨', '|')
    processed_statement_str = processed_statement_str.replace('¬', '~')
    processed_statement_str = processed_statement_str.replace('→', '>>')
    processed_statement_str = processed_statement_str.replace('↔', '==')
    try:
        expr = sympify(processed_statement_str, evaluate=False, locals=symbol_map)
        return expr
    except SympifyError as e:
        raise ValueError(f"Invalid logical statement syntax: {e}")
    except Exception as e:
        raise ValueError(f"An unexpected error occurred during parsing: {e}")

def get_all_symbols(statements):
    all_symbols = set()
    for stmt_expr in statements:
        all_symbols.update(stmt_expr.free_symbols)
    return sorted(list(all_symbols), key=str)

def generate_truth_table_data(statements):
    if not statements:
        return [], []
    all_symbols = get_all_symbols(statements)
    if not all_symbols:
        headers = ['Statement']
        rows = []
        for stmt_expr in statements:
            try:
                val = 'T' if stmt_expr == True else ('F' if stmt_expr == False else 'Error')
                rows.append({'Statement': val})
            except:
                rows.append({'Statement': 'Error'})
        return headers, rows
    headers = [str(s) for s in all_symbols] + [str(s) for s in statements]
    rows_data = []
    num_symbols = len(all_symbols)
    for i in range(2**num_symbols):
        assignment = {}
        binary_repr = bin(i)[2:].zfill(num_symbols)
        for j, symbol in enumerate(all_symbols):
            assignment[symbol] = (binary_repr[j] == '1')
        row = OrderedDict()
        for symbol in all_symbols:
            row[str(symbol)] = 'T' if assignment[symbol] else 'F'
        for stmt_expr in statements:
            try:
                evaluated_val = stmt_expr.subs(assignment)
                row[str(stmt_expr)] = 'T' if evaluated_val else 'F'
            except Exception as e:
                row[str(stmt_expr)] = 'Error'
        rows_data.append(row)
    return headers, rows_data

def run_truth_table_inference(knowledge_base_exprs, query_expr):
    if not knowledge_base_exprs:
        return False, ["Knowledge base is empty."], "No knowledge base."
    kb_combined = And(*knowledge_base_exprs)
    inference_expression = Implies(kb_combined, query_expr)
    is_derivable = valid(inference_expression)
    steps = [
        f"Knowledge Base (KB): {kb_combined}",
        f"Query (Q): {query_expr}",
        f"Checking if KB → Q is a tautology.",
        f"Result: KB → Q is {'TRUE' if is_derivable else 'FALSE'} for all truth assignments."
    ]
    return is_derivable, steps, str(query_expr)



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users.get(email)

        if user and check_password_hash(user['password_hash'], password):
            session['logged_in'] = True
            session['user_id'] = email
            session['statements'] = []
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']

        if not full_name or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')

        if email in users:
            flash('Email already registered. Please use a different email or log in.', 'error')
            return render_template('register.html')

        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        users[email] = {
            'full_name': full_name,
            'password_hash': hashed_password
        }

        flash(f'Registration successful for {full_name} ({email})! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('statements', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.before_request
def require_login():
    if request.endpoint not in ['login', 'register', 'static'] and not session.get('logged_in'):
        return redirect(url_for('login'))

@app.route('/api/add_statement', methods=['POST'])
def add_statement():
    data = request.get_json()
    statement_str = data.get('statement')
    if not statement_str:
        return jsonify({'success': False, 'message': 'Statement cannot be empty.'}), 400
    try:
        expr = parse_statement(statement_str)
        for stmt_data in session.get('statements', []):
            existing_expr = parse_statement(stmt_data['text'])
            if expr == existing_expr:
                return jsonify({'success': False, 'message': 'Statement already exists.'}), 409
        new_statement = {
            'id': str(uuid.uuid4()),
            'text': statement_str
        }
        session.setdefault('statements', []).append(new_statement)
        session.modified = True
        return jsonify({'success': True, 'message': 'Statement added successfully.'})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Error adding statement: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An unexpected server error occurred.'}), 500

@app.route('/api/get_statements', methods=['GET'])
def get_statements():
    return jsonify({'success': True, 'statements': session.get('statements', [])})

@app.route('/api/delete_statement', methods=['POST'])
def delete_statement():
    data = request.get_json()
    statement_id = data.get('id')
    if not statement_id:
        return jsonify({'success': False, 'message': 'Statement ID is required.'}), 400
    statements = session.get('statements', [])
    original_len = len(statements)
    session['statements'] = [s for s in statements if s['id'] != statement_id]
    session.modified = True
    if len(session['statements']) < original_len:
        return jsonify({'success': True, 'message': 'Statement deleted successfully.'})
    else:
        return jsonify({'success': False, 'message': 'Statement not found.'}), 404

@app.route('/api/generate_truth_table', methods=['POST'])
def generate_truth_table():
    statements_data = session.get('statements', [])
    if not statements_data:
        return jsonify({'success': False, 'message': 'No statements in knowledge base to generate truth table.'}), 400
    try:
        statements_exprs = [parse_statement(s['text']) for s in statements_data]
        headers, rows_data = generate_truth_table_data(statements_exprs)
        json_rows = [dict(row) for row in rows_data]
        return jsonify({'success': True, 'headers': headers, 'rows': json_rows})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Error generating truth table: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An unexpected server error occurred during truth table generation.'}), 500

@app.route('/api/run_inference', methods=['POST'])
def run_inference():
    data = request.get_json()
    query_str = data.get('query')
    method = data.get('method')
    if not query_str:
        return jsonify({'success': False, 'message': 'Query statement cannot be empty.'}), 400
    statements_data = session.get('statements', [])
    if not statements_data:
        return jsonify({'success': False, 'message': 'No statements in knowledge base to run inference.'}), 400
    try:
        knowledge_base_exprs = [parse_statement(s['text']) for s in statements_data]
        query_expr = parse_statement(query_str)
        is_derivable = False
        steps = []
        conclusion = query_str
        if method == 'truth-table':
            is_derivable, steps, conclusion = run_truth_table_inference(knowledge_base_exprs, query_expr)
        elif method == 'modus-ponens':
            steps = ["Modus Ponens inference is a placeholder.", "Please select 'Truth Table Check'."]
            is_derivable = False
        elif method == 'resolution':
            steps = ["Resolution inference is a placeholder.", "Please select 'Truth Table Check'."]
            is_derivable = False
        else:
            return jsonify({'success': False, 'message': 'Invalid inference method selected.'}), 400
        return jsonify({
            'success': True,
            'result': {
                'conclusion': conclusion,
                'derived': is_derivable,
                'steps': steps
            }
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        app.logger.error(f"Error running inference: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An unexpected server error occurred during inference.'}), 500

if __name__ == '__main__':
     app.run(debug=True)