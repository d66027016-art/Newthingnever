const { spawn } = require('child_process');
const path = require('path');

exports.handler = async (event, context) => {
  // Only accept POST requests from Telegram
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'healthy', message: 'Netlify Python Bot Bridge is active' }),
    };
  }

  return new Promise((resolve) => {
    try {
      // Spawn Python process executing our handler script
      const pythonScript = path.join(__dirname, 'bot_bridge.py');
      const py = spawn('python', [pythonScript]);

      let outputData = '';
      let errorData = '';

      // Send the request body (Telegram Update JSON) to Python's stdin
      py.stdin.write(event.body);
      py.stdin.end();

      py.stdout.on('data', (data) => {
        outputData += data.toString();
      });

      py.stderr.on('data', (data) => {
        errorData += data.toString();
      });

      py.on('close', (code) => {
        if (code !== 0) {
          console.error(`Python script exited with code ${code}. Error: ${errorData}`);
          resolve({
            statusCode: 500,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ error: errorData || 'Subprocess error' }),
          });
        } else {
          try {
            const result = JSON.parse(outputData.trim());
            resolve({
              statusCode: 200,
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(result),
            });
          } catch (e) {
            resolve({
              statusCode: 200,
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ status: 'ok', raw: outputData }),
            });
          }
        }
      });
    } catch (err) {
      console.error('Bridge exception:', err);
      resolve({
        statusCode: 500,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ error: err.message }),
      });
    }
  });
};
