fetch('http://localhost:8000/sessions')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error);

fetch('http://127.0.0.1:8000/sessions')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error);
