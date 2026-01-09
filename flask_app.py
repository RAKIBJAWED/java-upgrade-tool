from flask import Flask, render_template_string, request, jsonify
import os
import requests

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Java Version Compatibility Fixer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 1200px; margin: 0 auto; }
        textarea { width: 100%; height: 200px; font-family: monospace; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .result { margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 4px; }
        .error { background: #f8d7da; color: #721c24; }
        .success { background: #d4edda; color: #155724; }
        pre { white-space: pre-wrap; font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Java Version Compatibility Fixer</h1>
        <p>Enter your Java code below and get AI-powered compatibility fixes for different Java versions.</p>
        
        <form id="codeForm">
            <div>
                <label for="javaCode">Java Code:</label>
                <textarea id="javaCode" name="javaCode" placeholder="Enter your Java code here..."></textarea>
            </div>
            <div style="margin: 20px 0;">
                <label for="targetVersion">Target Java Version:</label>
                <select id="targetVersion" name="targetVersion">
                    <option value="8">Java 8</option>
                    <option value="11">Java 11</option>
                    <option value="17">Java 17</option>
                    <option value="21">Java 21</option>
                </select>
            </div>
            <button type="submit">Fix Compatibility Issues</button>
        </form>
        
        <div id="result"></div>
    </div>

    <script>
        document.getElementById('codeForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = '<div class="result">Processing...</div>';
            
            try {
                const response = await fetch('/fix', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    resultDiv.innerHTML = `
                        <div class="result success">
                            <h3>Fixed Code:</h3>
                            <pre>${result.fixed_code}</pre>
                            <h3>Explanation:</h3>
                            <p>${result.explanation}</p>
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `
                        <div class="result error">
                            <h3>Error:</h3>
                            <p>${result.error}</p>
                        </div>
                    `;
                }
            } catch (error) {
                resultDiv.innerHTML = `
                    <div class="result error">
                        <h3>Error:</h3>
                        <p>Failed to process request: ${error.message}</p>
                    </div>
                `;
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/fix', methods=['POST'])
def fix_code():
    try:
        data = request.get_json()
        java_code = data.get('javaCode', '').strip()
        target_version = data.get('targetVersion', '11')
        
        if not java_code:
            return jsonify({'success': False, 'error': 'Please provide Java code to fix'})
        
        # Simple mock response for now - in production this would call LLM
        fixed_code = f"""// Fixed for Java {target_version}
{java_code}

// Note: This is a demo version running in fallback mode.
// The actual implementation would analyze your code and provide
// specific fixes for Java {target_version} compatibility issues."""
        
        explanation = f"""This code has been analyzed for Java {target_version} compatibility. 
In the full version, this would include:
- Detection of deprecated APIs
- Suggestions for modern alternatives  
- Module system compatibility fixes
- Performance optimizations
- Security improvements"""
        
        return jsonify({
            'success': True,
            'fixed_code': fixed_code,
            'explanation': explanation
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
