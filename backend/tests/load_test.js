import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    http_req_failed: ['rate<0.01'], // error rate < 1%
    http_req_duration: ['p(95)<2000'], // 95% of requests < 2000ms
  },
};

const BASE_URL = 'http://127.0.0.1:8000/api';

// Retrieve authentication token before running VUs
export function setup() {
  const loginRes = http.post(`${BASE_URL}/auth/login`, {
    username: 'test@example.com',
    password: 'password123',
  }, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  const token = loginRes.json('access_token');
  if (!token) {
    throw new Error('Failed to retrieve token during setup. Login response was: ' + loginRes.body);
  }
  return { token };
}

export default function (data) {
  const headers = {
    'Authorization': `Bearer ${data.token}`,
    'Content-Type': 'application/json',
  };

  // 1. Fetch available models
  const modelsRes = http.get(`${BASE_URL}/models`, { headers });
  check(modelsRes, {
    'models status is 200': (r) => r.status === 200,
    'has models list': (r) => r.json().length > 0,
  });

  sleep(0.5);

  // 2. Submit a synchronous Q&A query (uses EchoLLM)
  const askRes = http.post(`${BASE_URL}/ask`, JSON.stringify({
    question: 'What is load testing?',
    model_id: 'echo',
    workspace_id: 'workspace-id-1',
  }), { headers });
  
  check(askRes, {
    'ask status is 200': (r) => r.status === 200,
    'ask answer contains text': (r) => r.json('answer').length > 0,
  });

  sleep(0.5);

  // 3. Submit an async workflow task to the queue
  const submitRes = http.post(`${BASE_URL}/workflows/submit`, JSON.stringify({
    question: `Load testing task from VU ${__VU}`,
    workspace_id: 'workspace-id-1',
  }), { headers });

  const isSubmitOk = check(submitRes, {
    'workflow submit is 201': (r) => r.status === 201,
    'workflow has ID': (r) => r.json('workflow_id') !== undefined,
  });

  if (isSubmitOk) {
    const workflowId = submitRes.json('workflow_id');
    
    // Poll the status of the workflow up to 5 times (max 5 seconds wait per VU loop)
    let completed = false;
    for (let i = 0; i < 5; i++) {
      sleep(1);
      const statusRes = http.get(`${BASE_URL}/workflows/${workflowId}/status`, { headers });
      
      check(statusRes, {
        'status request is 200': (r) => r.status === 200,
      });

      const status = statusRes.json('status');
      if (status === 'COMPLETED' || status === 'FAILED') {
        completed = true;
        break;
      }
    }
  }

  sleep(1);
}
