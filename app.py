import streamlit as st
from sympy import symbols, SympifyError, sympify
from sympy.logic.boolalg import And, Or, Not, Implies, Equivalent
from sympy.logic.inference import satisfiable, valid
from collections import OrderedDict
import re

# (Keep your backend logic functions here, e.g., parse_statement, get_all_symbols, generate_truth_table_data, run_truth_table_inference)
# ... (your existing functions like parse_statement, get_all_symbols, etc. go here) ...

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


# --- Streamlit UI starts here ---
st.set_page_config(layout="wide", page_title="Logic Learning Platform")

st.title("Logic Learning Platform")
st.markdown("Interactive tools to help you understand logic statements, truth tables, and inference rules.")

# Initialize session state for statements if not already present
if 'statements' not in st.session_state:
    st.session_state.statements = []

# Logic Input Section
st.header("Logic Input")
statement_input = st.text_input(
    "Enter a logical statement (e.g., (P & Q) >> R)",
    key="logic_statement_input"
)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    if st.button("∧ AND"):
        st.session_state.logic_statement_input += " ∧ "
with col2:
    if st.button("∨ OR"):
        st.session_state.logic_statement_input += " ∨ "
with col3:
    if st.button("¬ NOT"):
        st.session_state.logic_statement_input += "¬"
with col4:
    if st.button("→ IMPLIES"):
        st.session_state.logic_statement_input += " → "
with col5:
    if st.button("↔ IFF"):
        st.session_state.logic_statement_input += " ↔ "

if st.button("Add Statement to Knowledge Base"):
    if statement_input:
        try:
            # Validate and parse the statement
            parsed_expr = parse_statement(statement_input)
            # Check for duplicates
            if any(parse_statement(s['text']) == parsed_expr for s in st.session_state.statements):
                st.warning("This statement already exists in the knowledge base.")
            else:
                st.session_state.statements.append({'id': str(len(st.session_state.statements)), 'text': statement_input})
                st.success(f"Added: `{statement_input}`")
        except ValueError as e:
            st.error(f"Error: {e}")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
    else:
        st.warning("Please enter a statement.")

st.markdown("---")

# Knowledge Base and Truth Table Sections
col_kb, col_tt = st.columns(2)

with col_kb:
    st.header("Knowledge Base")
    if st.session_state.statements:
        for i, stmt_data in enumerate(st.session_state.statements):
            display_col, delete_col = st.columns([0.8, 0.2])
            with display_col:
                st.write(f"**{i+1}.** `{stmt_data['text']}`")
            with delete_col:
                if st.button("Delete", key=f"delete_btn_{stmt_data['id']}"):
                    st.session_state.statements.pop(i)
                    st.experimental_rerun() # Rerun to update the list
    else:
        st.info("Knowledge base is empty. Add statements above.")

with col_tt:
    st.header("Truth Table")
    if st.button("Generate Truth Table"):
        if st.session_state.statements:
            try:
                statements_exprs = [parse_statement(s['text']) for s in st.session_state.statements]
                headers, rows_data = generate_truth_table_data(statements_exprs)

                # Convert OrderedDict rows to list of lists for st.table or st.dataframe
                if rows_data:
                    df_data = []
                    for row in rows_data:
                        df_data.append(list(row.values()))
                    st.dataframe(df_data, column_names=headers, hide_index=True)
                else:
                    st.info("No truth table generated (e.g., no symbols in statements).")

            except ValueError as e:
                st.error(f"Error generating truth table: {e}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
        else:
            st.warning("Add statements to the knowledge base first.")

st.markdown("---")

# Inference Engine Section
st.header("Inference Engine")
query_input = st.text_input("Enter a query statement for inference (e.g., R)", key="query_input")
inference_method = st.selectbox(
    "Select Inference Method",
    ["Truth Table Check", "Modus Ponens (Placeholder)", "Resolution (Placeholder)"],
    key="inference_method_select"
)

if st.button("Run Inference"):
    if not st.session_state.statements:
        st.warning("Add statements to the knowledge base first.")
    elif not query_input:
        st.warning("Please enter a query statement.")
    else:
        try:
            knowledge_base_exprs = [parse_statement(s['text']) for s in st.session_state.statements]
            query_expr = parse_statement(query_input)

            if inference_method == "Truth Table Check":
                is_derivable, steps, conclusion = run_truth_table_inference(knowledge_base_exprs, query_expr)
                st.subheader("Inference Result")
                if is_derivable:
                    st.success(f"Conclusion `{conclusion}` is derivable from the knowledge base.")
                else:
                    st.error(f"Conclusion `{conclusion}` is NOT derivable from the knowledge base.")
                st.write("--- Steps ---")
                for step in steps:
                    st.markdown(f"- {step}")
            else:
                st.info(f"'{inference_method}' is a placeholder. Please select 'Truth Table Check'.")

        except ValueError as e:
            st.error(f"Error: {e}")
        except Exception as e:
            st.error(f"An unexpected error occurred during inference: {e}")