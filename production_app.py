from flask import Flask, render_template_string, request, jsonify
import os
import requests
import anthropic

app = Flask(__name__)

# Initialize LLM clients
anthropic_client = None
if os.getenv('ANTHROPIC_API_KEY'):
    anthropic_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Java Version Compatibility Fixer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        textarea { width: 100%; height: 200px; font-family: 'Courier New', monospace; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        button { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #0056b3; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .result { margin-top: 30px; padding: 20px; border-radius: 4px; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .loading { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        pre { white-space: pre-wrap; font-family: 'Courier New', monospace; background: #f8f9fa; padding: 15px; border-radius: 4px; overflow-x: auto; }
        .code-section { margin: 15px 0; }
        .code-title { font-weight: bold; margin-bottom: 10px; color: #333; }
        .provider-info { text-align: center; margin-bottom: 20px; padding: 10px; background: #e7f3ff; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Java Version Compatibility Fixer</h1>
            <p>AI-powered Java code modernization and compatibility fixes</p>
        </div>
        
        <div class="provider-info">
            <strong>🤖 Powered by:</strong> Anthropic Claude & Together AI
        </div>
        
        <form id="codeForm">
            <div class="form-group">
                <label for="javaCode">Java Code:</label>
                <textarea id="javaCode" name="javaCode" placeholder="Paste your Java code here...

Example:
public class Example {
    public static void main(String[] args) {
        Vector<String> list = new Vector<>();
        list.addElement(\"Hello\");
        System.out.println(list.elementAt(0));
    }
}"></textarea>
            </div>
            
            <div class="form-group">
                <label for="targetVersion">Target Java Version:</label>
                <select id="targetVersion" name="targetVersion">
                    <option value="8">Java 8 (LTS)</option>
                    <option value="11" selected>Java 11 (LTS)</option>
                    <option value="17">Java 17 (LTS)</option>
                    <option value="21">Java 21 (LTS)</option>
                </select>
            </div>
            
            <button type="submit" id="submitBtn">🔧 Fix Compatibility Issues</button>
        </form>
        
        <div id="result"></div>
    </div>

    <script>
        document.getElementById('codeForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            
            if (!data.javaCode.trim()) {
                document.getElementById('result').innerHTML = `
                    <div class="result error">
                        <h3>❌ Error:</h3>
                        <p>Please provide Java code to analyze.</p>
                    </div>
                `;
                return;
            }
            
            const resultDiv = document.getElementById('result');
            const submitBtn = document.getElementById('submitBtn');
            
            submitBtn.disabled = true;
            submitBtn.textContent = '🔄 Processing...';
            
            resultDiv.innerHTML = `
                <div class="result loading">
                    <h3>🤖 AI Analysis in Progress...</h3>
                    <p>Analyzing your Java code for compatibility issues with Java ${data.targetVersion}...</p>
                </div>
            `;
            
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
                            <h3>✅ Code Analysis Complete</h3>
                            
                            <div class="code-section">
                                <div class="code-title">🔧 Fixed Code for Java ${data.targetVersion}:</div>
                                <pre>${result.fixed_code}</pre>
                            </div>
                            
                            <div class="code-section">
                                <div class="code-title">📋 Analysis & Recommendations:</div>
                                <div style="background: #f8f9fa; padding: 15px; border-radius: 4px;">
                                    ${result.explanation.replace(/\\n/g, '<br>')}
                                </div>
                            </div>
                            
                            <div style="margin-top: 15px; font-size: 12px; color: #666;">
                                <strong>Powered by:</strong> ${result.provider || 'Anthropic Claude'}
                            </div>
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `
                        <div class="result error">
                            <h3>❌ Error:</h3>
                            <p>${result.error}</p>
                        </div>
                    `;
                }
            } catch (error) {
                resultDiv.innerHTML = `
                    <div class="result error">
                        <h3>❌ Network Error:</h3>
                        <p>Failed to process request: ${error.message}</p>
                    </div>
                `;
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = '🔧 Fix Compatibility Issues';
            }
        });
    </script>
</body>
</html>
"""

def call_together_ai(prompt):
    """Call Together AI API"""
    try:
        response = requests.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('TOGETHER_AI_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/Llama-2-7b-chat-hf",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000,
                "temperature": 0.1
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Together AI error: {e}")
    return None

def call_anthropic(prompt):
    """Call Anthropic Claude API"""
    try:
        if anthropic_client:
            response = anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
    except Exception as e:
        print(f"Anthropic error: {e}")
    return None

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
            return jsonify({'success': False, 'error': 'Please provide Java code to analyze'})
        
        # Create prompt for LLM
        prompt = f"""You are a Java expert. Analyze this Java code for compatibility with Java {target_version} and provide fixes.

Original Code:
```java
{java_code}
```

Target Java Version: {target_version}

Please provide:
1. Fixed/modernized code that works with Java {target_version}
2. Explanation of changes made
3. Best practices recommendations

Focus on:
- Deprecated API usage
- Modern collection types
- Lambda expressions (Java 8+)
- Stream API usage
- Module system compatibility (Java 9+)
- Performance improvements

Respond with the fixed code first, then explanation."""

        # Try Anthropic first, then Together AI as fallback
        result = call_anthropic(prompt)
        provider = "Anthropic Claude"
        
        if not result:
            result = call_together_ai(prompt)
            provider = "Together AI"
        
        if not result:
            return jsonify({
                'success': False, 
                'error': 'LLM services unavailable. Please check API keys and try again.'
            })
        
        # Parse the result to separate code and explanation
        parts = result.split('```java')
        if len(parts) > 1:
            code_part = parts[1].split('```')[0].strip()
            explanation_part = result.split('```')[-1].strip()
        else:
            # Fallback parsing
            lines = result.split('\n')
            code_lines = []
            explanation_lines = []
            in_code = False
            
            for line in lines:
                if 'public class' in line or 'import ' in line:
                    in_code = True
                if in_code and (line.strip() == '' or 'Explanation:' in line or 'Changes made:' in line):
                    in_code = False
                    continue
                    
                if in_code:
                    code_lines.append(line)
                else:
                    explanation_lines.append(line)
            
            code_part = '\n'.join(code_lines).strip() or java_code
            explanation_part = '\n'.join(explanation_lines).strip()
        
        if not explanation_part:
            explanation_part = f"Code has been analyzed and optimized for Java {target_version} compatibility."
        
        return jsonify({
            'success': True,
            'fixed_code': code_part,
            'explanation': explanation_part,
            'provider': provider
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Processing error: {str(e)}'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
