const addBtn = document.getElementById("addStatementBtn");
const input = document.getElementById("logicStatement");
const list = document.getElementById("statementsList");
const runInferenceBtn = document.getElementById("runInferenceBtn");
const inferenceResult = document.getElementById("inferenceResult");
const generateTruthTableBtn = document.getElementById("generateTruthTableBtn");
const truthTableContainer = document.getElementById("truthTableResult");
const inputMessage = document.getElementById("inputMessage");
const kbEmptyState = document.getElementById("kbEmptyState");
const methodSelect = document.getElementById("methodSelect"); // Added for inference method
const queryStatementInput = document.getElementById("queryStatement"); // Added for inference query

let messageTimer;

function showMessage(text, type = "muted") {
    if (!inputMessage) return;
    inputMessage.textContent = text;
    inputMessage.className = `message ${type}`;
    clearTimeout(messageTimer);
    if (type === "success") {
        messageTimer = setTimeout(() => {
            inputMessage.textContent = "";
            inputMessage.className = "message muted";
        }, 2000);
    }
}

function updateKbEmptyState() {
    if (!kbEmptyState || !list) return;
    const hasItems = !!list.querySelector("li");
    kbEmptyState.style.display = hasItems ? "none" : "block";
}

function hasBalancedParentheses(expr) {
    let balance = 0;
    for (const ch of expr) {
        if (ch === "(") balance++;
        else if (ch === ")") balance--;
        if (balance < 0) return false;
    }
    return balance === 0;
}

function normalizeInput(expr) {
    return expr
        .replace(/˄/g, "∧")
        .replace(/˅/g, "∨")
        .replace(/\^/g, "∧")
        .replace(/\bv\b/g, "∨");
}

function validateInput(raw) {
    const expr = raw.trim();
    if (expr.length === 0) {
        return { ok: false, message: "Type a logical statement first." };
    }
    const allowed = /^[A-Za-z0-9\s()¬∧∨→↔]+$/;
    if (!allowed.test(expr)) {
        return {
            ok: false,
            message: "Invalid character found. Use letters, numbers, (), and operators ¬ ∧ ∨ → ↔ only."
        };
    }
    if (!hasBalancedParentheses(expr)) {
        return { ok: false, message: "Unbalanced parentheses. Check your ( and )." };
    }
    const trimmed = expr.replace(/\s+/g, " ");
    if (/[∧∨→↔]\s*$/.test(trimmed)) {
        return { ok: false, message: "Expression cannot end with an operator." };
    }
    if (/^\s*[∧∨→↔]/.test(trimmed)) {
        return { ok: false, message: "Expression cannot start with a binary operator." };
    }
    if (/[∧∨→↔]\s*[∧∨→↔]/.test(trimmed)) {
        return { ok: false, message: "Two operators in a row. Check your expression." };
    }
    if (/\(\s*\)/.test(trimmed)) {
        return { ok: false, message: "Empty parentheses detected. Remove () or add content." };
    }
    return { ok: true, message: "Valid expression." };
}

function insertAtCursor(el, text) {
    if (!el) return;
    if (typeof text !== "string") return;
    const start = typeof el.selectionStart === "number" ? el.selectionStart : el.value.length;
    const end = typeof el.selectionEnd === "number" ? el.selectionEnd : el.value.length;
    el.value = el.value.slice(0, start) + text + el.value.slice(end);
    el.focus();
    el.selectionStart = el.selectionEnd = start + text.length;
}


async function fetchAndDisplayStatements() {
    try {
        const response = await fetch("/api/get_statements");
        const data = await response.json();

        if (data.success) {
            list.innerHTML = ""; 
            data.statements.forEach(stmt => {
                const li = document.createElement("li");
                li.setAttribute("data-id", stmt.id); 
                const textSpan = document.createElement("span");
                textSpan.textContent = stmt.text;
                const deleteBtn = document.createElement("button");
                deleteBtn.type = "button";
                deleteBtn.textContent = "Delete";
                deleteBtn.className = "delete-btn";
                deleteBtn.addEventListener("click", () => deleteStatement(stmt.id, li));

                li.appendChild(textSpan);
                li.appendChild(deleteBtn);
                list.appendChild(li);
            });
            updateKbEmptyState();
        } else {
            showMessage(`Error loading statements: ${data.message}`, "error");
        }
    } catch (error) {
        console.error("Error fetching statements:", error);
        showMessage("Failed to load statements from server.", "error");
    }
}


async function deleteStatement(id, listItem) {
    try {
        const response = await fetch("/api/delete_statement", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ id: id })
        });
        const data = await response.json();

        if (data.success) {
            listItem.remove();
            updateKbEmptyState();
            showMessage("Statement removed.", "muted");
        } else {
            showMessage(`Error deleting statement: ${data.message}`, "error");
        }
    } catch (error) {
        console.error("Error deleting statement:", error);
        showMessage("Failed to delete statement from server.", "error");
    }
}


if (input) {
    input.addEventListener("input", () => {
        input.value = normalizeInput(input.value);
        showMessage("", "muted");
    });
}

document.querySelectorAll(".op-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        const op = btn.getAttribute("data-op");
        if (!op) return;
        const normalizedOp = normalizeInput(op);
        const spaced =
            normalizedOp === "∧" || normalizedOp === "∨" || normalizedOp === "→" || normalizedOp === "↔"
                ? ` ${normalizedOp} `
                : normalizedOp;
        insertAtCursor(input, spaced);
        input.value = normalizeInput(input.value); 
    });
});

if (addBtn) {
    addBtn.addEventListener("click", async () => { 
        const normalized = normalizeInput(input.value);
        const statement = normalized.trim();
        const check = validateInput(statement);

        if (!check.ok) {
            showMessage(check.message, "error");
            return;
        }

        
        try {
            const response = await fetch("/api/add_statement", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ statement: statement })
            });
            const data = await response.json();

            if (data.success) {
                input.value = "";
                showMessage("Statement added to knowledge base.", "success");
                fetchAndDisplayStatements(); 
            } else {
                showMessage(`Error: ${data.message}`, "error");
            }
        } catch (error) {
            console.error("Error adding statement:", error);
            showMessage("Failed to add statement to server.", "error");
        }
    });
}

if (runInferenceBtn) {
    runInferenceBtn.addEventListener("click", async () => {
        const statements = Array.from(list.querySelectorAll("li span")).map((s) => s.textContent);
        const query = queryStatementInput.value.trim(); // Get query from new input
        const selectedMethod = methodSelect.value;

        if (statements.length === 0) {
            inferenceResult.innerHTML = '<p class="muted">Add at least one statement to the Knowledge Base first.</p>';
            return;
        }
        if (!query) {
            inferenceResult.innerHTML = '<p class="muted">Please enter a query statement.</p>';
            return;
        }

        inferenceResult.innerHTML = '<p class="muted">Running inference...</p>';

        try {
            const response = await fetch("/api/run_inference", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ statements: statements, query: query, method: selectedMethod })
            });
            const data = await response.json();

            if (data.success) {
                const result = data.result;
                let html = `<strong>Query:</strong> ${result.conclusion}<br>`;
                html += `<strong>Derived:</strong> <span class="${result.derived ? 'true' : 'false'}">${result.derived ? 'TRUE' : 'FALSE'}</span><br>`;
                html += `<strong>Method:</strong> ${selectedMethod}<br>`;
                html += `<strong>Steps:</strong><ol>`;
                result.steps.forEach(step => {
                    html += `<li>${step}</li>`;
                });
                html += `</ol>`;
                inferenceResult.innerHTML = html;
            } else {
                inferenceResult.innerHTML = `<p class="message error">Error: ${data.message}</p>`;
            }
        } catch (error) {
            console.error("Error running inference:", error);
            inferenceResult.innerHTML = '<p class="message error">Failed to run inference from server.</p>';
        }
    });
}

if (generateTruthTableBtn) {
    generateTruthTableBtn.addEventListener("click", async () => { 
        const statements = Array.from(list.querySelectorAll("li span")).map((s) => s.textContent);

        if (!truthTableContainer) return;

        if (statements.length === 0) {
            truthTableContainer.innerHTML =
                '<p class="muted">Add at least one statement first to generate a truth table.</p>';
            return;
        }

        truthTableContainer.innerHTML = '<p class="muted">Generating truth table...</p>';

        try {
            const response = await fetch("/api/generate_truth_table", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ statements: statements })
            });
            const data = await response.json();

            if (data.success) {
                const headers = data.headers;
                const rows = data.rows;

                let tableHtml = `<table><thead><tr>`;
                headers.forEach(h => {
                    tableHtml += `<th>${h}</th>`;
                });
                tableHtml += `</tr></thead><tbody>`;

                rows.forEach(row => {
                    tableHtml += `<tr>`;
                    headers.forEach(h => {
                        const val = row[h];
                        const className = val === "T" ? "true" : (val === "F" ? "false" : "");
                        tableHtml += `<td class="${className}">${val}</td>`;
                    });
                    tableHtml += `</tr>`;
                });
                tableHtml += `</tbody></table>`;
                truthTableContainer.innerHTML = tableHtml;
            } else {
                truthTableContainer.innerHTML = `<p class="message error">Error: ${data.message}</p>`;
            }
        } catch (error) {
            console.error("Error generating truth table:", error);
            truthTableContainer.innerHTML = '<p class="message error">Failed to generate truth table from server.</p>';
        }
    });
}


document.addEventListener("DOMContentLoaded", fetchAndDisplayStatements);
updateKbEmptyState(); 