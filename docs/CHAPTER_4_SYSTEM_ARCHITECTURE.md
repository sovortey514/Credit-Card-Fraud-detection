# Chapter 4: System Architecture and Web Prototype

## 4.1 Overview

The prototype supports investigation of credit-card fraud predictions using a React dashboard, FastAPI services, a MySQL user directory, and a chronological replay of held-out transactions. This chapter describes the implementation and does not claim production deployment or measured performance.

## 4.2 Components

The browser presents a transaction feed, aggregate indicators, and an alert inspection panel. The fraud API loads trained models and preprocessing artifacts to score transactions and provide TreeSHAP explanations. Its replay engine reads the held-out Parquet split in chronological order and streams scored events over WebSocket. A separate authentication service manages user accounts and issues bearer tokens, with MySQL storing account and token records.

## 4.3 Transaction and explanation flow

The browser opens a replay session specifying a model and rate. The replay engine orders the test split by elapsed Time, scores each transaction, and waits for an acknowledgement of each sequence. When an alert is inspected, the browser requests the explanation for that sequence and model. The API retrieves the corresponding held-out transaction, applies the saved preprocessing pipeline, and returns the strongest signed SHAP contributions. The chart shows contribution magnitude and direction; the base value and contributions are in the explainer's model-output units and should not be assumed to be probabilities.

## 4.4 Deployment and limitations

Docker Compose defines the dashboard, fraud API with replay engine, authentication API, and MySQL. The model, processed data, and report directories are mounted from the host; trained artifacts and the held-out split must exist before startup. The browser connects to the services on localhost ports 5173, 8000, and 8001. The implementation requires local verification of startup, endpoint behavior, and resource consumption; a successful build alone does not establish operational performance or zero dropped messages.

## 4.5 Security and evaluation

User-management endpoints use JWT bearer authentication and role checks. Fraud inference and replay endpoints should be considered prototype interfaces: access control, transport security, deployment configuration, and risk assessment require further work before use with real transaction data. Evaluation should separately document predictive performance, explanation behavior, and end-to-end latency.
