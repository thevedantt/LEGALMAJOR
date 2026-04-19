// next.config.js
module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/overall-risk',
        destination: 'http://localhost:8000/overall-risk', // Proxy to FastAPI
      },
      {
        source: '/api/analyze-risk',
        destination: 'http://localhost:8000/analyze-risk',
      },
      {
        source: '/api/summarize',
        destination: 'http://localhost:8000/summarize',
      },
      {
        source: '/api/ask',
        destination: 'http://localhost:8000/ask',
      },
      {
        source: '/api/upload',
        destination: 'http://localhost:8000/upload',
      },
      {
        source: '/api/fairness',
        destination: 'http://localhost:8000/fairness',
      },
      {
        source: '/api/check-conflicts',
        destination: 'http://localhost:8000/check-conflicts',
      },
      {
        source: '/api/extract-clauses',
        destination: 'http://localhost:8000/extract-clauses',
      },
      {
        source: '/api/explain-term',
        destination: 'http://localhost:8000/explain-term',
      },
      {
        source: '/api/suggest-improvements',
        destination: 'http://localhost:8000/suggest-improvements',
      },
      {
        source: '/api/generate-report',
        destination: 'http://localhost:8000/generate-report',
      },
    ];
  },
};
