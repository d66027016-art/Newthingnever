const { spawn } = require('child_process');
const path = require('path');

exports.handler = async (event, context) => {
  return new Promise((resolve) => {
    try {
      const pythonScript = path.join(__dirname, 'api_bridge.py');
      const py = spawn('python', [pythonScript]);

      let outputData = '';
      let errorData = '';

      // Pass the entire event object to Python stdin as JSON
      py.stdin.write(JSON.stringify(event));
      py.stdin.end();

      py.stdout.on('data', (data) => {
        outputData += data.toString();
      });

      py.stderr.on('data', (data) => {
        errorData += data.toString();
      });

      py.on('close', (code) => {
        if (code !== 0) {
          console.error(`Python API script exited with code ${code}. Error: ${errorData}`);
          resolve({
            statusCode: 500,
            headers: { 
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': '*',
              'Access-Control-Allow-Headers': 'Content-Type, X-API-Key',
              'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
            },
            body: JSON.stringify({ error: errorData || 'Subprocess API error' }),
          });
        } else {
          try {
            // The python script will print the exact Lambda response format {"statusCode": 200, "headers": ..., "body": ...}
            const response = JSON.parse(outputData.trim());
            resolve(response);
          } catch (e) {
            resolve({
              statusCode: 200,
              headers: { 
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, X-API-Key',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
              },
              body: JSON.stringify({ status: 'ok', raw: outputData }),
            });
          }
        }
      });
    } catch (err) {
      console.error('API bridge exception:', err);
      resolve({
        statusCode: 500,
        headers: { 
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Headers': 'Content-Type, X-API-Key',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
        },
        body: JSON.stringify({ error: err.message }),
      });
    }
  });
};
