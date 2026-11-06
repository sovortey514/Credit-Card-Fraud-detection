
$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host " FRAUD DETECTION DASHBOARD SETUP"
Write-Host "========================================"

# Always work from the project root
Set-Location $PSScriptRoot

# Check Node.js
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js/npm not found. Install Node.js LTS first."
}

Write-Host "`n[1/5] Checking frontend project..."

if (-not (Test-Path "frontend")) {
    New-Item -ItemType Directory -Path "frontend" | Out-Null
}

Set-Location "frontend"

# Create Vite React TypeScript only if not initialized
if (-not (Test-Path "package.json")) {
    Write-Host "Creating React + TypeScript project..."
    npm create vite@latest . -- --template react-ts

    if ($LASTEXITCODE -ne 0) {
        throw "Vite initialization failed."
    }
}

Write-Host "`n[2/5] Installing frontend dependencies..."

npm install

if ($LASTEXITCODE -ne 0) {
    throw "npm install failed."
}

New-Item -ItemType Directory -Force -Path "src" | Out-Null

Write-Host "`n[3/5] Creating React dashboard..."

# Back up existing files before replacement
foreach ($file in @("src/App.tsx", "src/App.css")) {
    if (Test-Path $file) {
        Copy-Item $file "$file.bak" -Force
    }
}

$appCode = @'
import { useState, type FormEvent } from "react";
import "./App.css";

type Prediction = {
  fraud_probability: number;
  is_fraud: boolean;
  threshold: number;
  inference_latency_ms: number;
};

export default function App() {
  const [amount, setAmount] = useState("10000");
  const [balance, setBalance] = useState("15000");
  const [step, setStep] = useState("400");
  const [result, setResult] = useState<Prediction | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/predict",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            amount: Number(amount),
            oldbalanceOrg: Number(balance),
            step: Number(step),
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data: Prediction = await response.json();
      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Prediction failed"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="dashboard">
      <header className="header">
        <div>
          <span className="eyebrow">MASTER'S RESEARCH PROTOTYPE</span>
          <h1>Money Transfer Fraud Detection</h1>
          <p>Real-time transaction analysis powered by XGBoost</p>
        </div>
        <span className="model-badge">XGBoost Model</span>
      </header>

      <section className="layout">
        <div className="panel">
          <h2>Transaction Details</h2>
          <p>Enter a simulated transfer to analyze.</p>

          <form onSubmit={handleSubmit}>
            <label>
              Transfer Amount
              <input
                type="number"
                min="0"
                step="any"
                required
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </label>

            <label>
              Sender's Balance Before Transfer
              <input
                type="number"
                min="0"
                step="any"
                required
                value={balance}
                onChange={(e) => setBalance(e.target.value)}
              />
            </label>

            <label>
              Simulation Time Step
              <input
                type="number"
                min="1"
                step="1"
                required
                value={step}
                onChange={(e) => setStep(e.target.value)}
              />
            </label>

            <button type="submit" disabled={loading}>
              {loading ? "Analyzing..." : "Analyze Transaction"}
            </button>
          </form>
        </div>

        <div className="panel">
          <h2>Fraud Detection Result</h2>

          {error && <div className="error">{error}</div>}

          {!result && !error && (
            <div className="empty">
              Submit a transaction to see the prediction.
            </div>
          )}

          {result && (
            <div>
              <div className={
                result.is_fraud
                  ? "status fraud"
                  : "status legitimate"
              }>
                {result.is_fraud
                  ? "⚠ Suspicious Transaction"
                  : "✓ No Fraud Flag"}
              </div>

              <div className="metric">
                <span>Model Fraud Score</span>
                <strong>
                  {(result.fraud_probability * 100).toFixed(2)}%
                </strong>
              </div>

              <div className="progress">
                <div style={{
                  width: `${result.fraud_probability * 100}%`
                }} />
              </div>

              <div className="metric">
                <span>Decision Threshold</span>
                <strong>
                  {(result.threshold * 100).toFixed(0)}%
                </strong>
              </div>

              <div className="metric">
                <span>Inference Latency</span>
                <strong>
                  {result.inference_latency_ms.toFixed(3)} ms
                </strong>
              </div>

              <p className="disclaimer">
                Synthetic-data research prototype.
                Model scores are not calibrated real-world
                fraud probabilities.
              </p>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
'@

Set-Content -Path "src/App.tsx" -Value $appCode -Encoding utf8

$cssCode = @'
* { box-sizing: border-box; }

body {
  margin: 0;
  background: #f3f6fb;
  color: #172338;
  font-family: Inter, Arial, sans-serif;
}

.dashboard {
  max-width: 1150px;
  margin: 0 auto;
  padding: 48px 24px;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 36px;
}

.eyebrow {
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1.5px;
}

h1 { font-size: 32px; margin: 12px 0; }
.header p, .panel p { color: #64748b; }

.model-badge {
  background: #dbeafe;
  color: #1d4ed8;
  padding: 10px 16px;
  border-radius: 20px;
  font-weight: 600;
  white-space: nowrap;
}

.layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.panel {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 28px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}

.panel h2 { margin-top: 0; }

form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-top: 28px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
}

input {
  padding: 13px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 16px;
}

input:focus {
  outline: 2px solid #93c5fd;
  border-color: #2563eb;
}

button {
  background: #2563eb;
  color: white;
  padding: 14px;
  border: none;
  border-radius: 8px;
  font-weight: 700;
  cursor: pointer;
}

button:disabled {
  opacity: 0.6;
  cursor: wait;
}

.status {
  padding: 18px;
  border-radius: 10px;
  font-weight: 700;
  margin: 25px 0;
}

.fraud { background: #fee2e2; color: #b91c1c; }
.legitimate { background: #dcfce7; color: #166534; }

.metric {
  display: flex;
  justify-content: space-between;
  margin: 24px 0 12px;
}

.metric strong { font-size: 20px; }

.progress {
  height: 12px;
  background: #e2e8f0;
  border-radius: 20px;
  overflow: hidden;
}

.progress div {
  height: 100%;
  background: #2563eb;
}

.empty {
  padding: 70px 15px;
  text-align: center;
  color: #94a3b8;
}

.error {
  padding: 16px;
  background: #fee2e2;
  color: #b91c1c;
  border-radius: 8px;
}

.disclaimer {
  font-size: 12px;
  line-height: 1.6;
  margin-top: 28px;
}

@media (max-width: 750px) {
  .layout { grid-template-columns: 1fr; }
  .header {
    align-items: flex-start;
    flex-direction: column;
  }
}
'@

Set-Content -Path "src/App.css" -Value $cssCode -Encoding utf8

Write-Host "`n[4/5] Configuring FastAPI CORS..."

Set-Location $PSScriptRoot

$backendPath = "backend/main.py"

if (-not (Test-Path $backendPath)) {
    throw "backend/main.py not found."
}

$backendCode = Get-Content $backendPath -Raw

if ($backendCode -notmatch 'from fastapi.middleware.cors import CORSMiddleware') {
    $backendCode = "from fastapi.middleware.cors import CORSMiddleware`n" + $backendCode
}

if ($backendCode -notmatch 'app\.add_middleware\(') {
    $corsBlock = @'

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

'@

    # Insert before the first route decorator.
    # This preserves the existing FastAPI app declaration.
    $marker = '@app.get("/")'

    if ($backendCode.Contains($marker)) {
        $backendCode = $backendCode.Replace(
            $marker,
            $corsBlock + "`n" + $marker
        )
    }
    else {
        throw "Homepage route not found. Add CORS manually after app = FastAPI(...)."
    }
}

Copy-Item $backendPath "$backendPath.bak" -Force
Set-Content -Path $backendPath -Value $backendCode -Encoding utf8

Write-Host "`n[5/5] Checking frontend build..."

Set-Location "frontend"

npm run build

if ($LASTEXITCODE -ne 0) {
    throw "Frontend build failed. Review the error above."
}

Set-Location $PSScriptRoot

Write-Host ""
Write-Host "========================================"
Write-Host " DASHBOARD SETUP COMPLETED"
Write-Host "========================================"
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Frontend: http://localhost:5173"
Write-Host ""
Write-Host "Start backend and frontend in separate terminals."
