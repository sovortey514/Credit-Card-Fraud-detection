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
