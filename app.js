document.addEventListener('DOMContentLoaded', () => {
    // ─── Docs Code Tab Switcher ───
    const codeTabs = document.querySelectorAll('[data-tab]');
    const codeDisplay = document.getElementById('code-display');

    const codeTemplates = {
        python: `import requests

url = "https://newthingnever.netlify.app/.netlify/functions/api/check"
headers = {
    "X-API-Key": "YOUR_API_KEY",
    "Content-Type": "application/json"
}
payload = {
    "url": "https://checkout.stripe.com/c/pay/cs_live_...",
    "card": "4532010000000000|12|29|123"
}

response = requests.post(url, headers=headers, json=payload)
print(response.json())`,
        nodejs: `const axios = require('axios');

const url = 'https://newthingnever.netlify.app/.netlify/functions/api/check';
const headers = {
    'X-API-Key': 'YOUR_API_KEY',
    'Content-Type': 'application/json'
};
const data = {
    url: 'https://checkout.stripe.com/c/pay/cs_live_...',
    card: '4532010000000000|12|29|123'
};

axios.post(url, data, { headers })
    .then(res => console.log(res.data))
    .catch(err => console.error(err.response.data));`,
        curl: `curl -X POST https://newthingnever.netlify.app/.netlify/functions/api/check \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://checkout.stripe.com/c/pay/cs_live_...",
    "card": "4532010000000000|12|29|123"
  }'`
    };

    codeTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            codeTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const lang = tab.getAttribute('data-tab');
            codeDisplay.textContent = codeTemplates[lang];
        });
    });

    // Set initial python code
    if (codeDisplay) {
        codeDisplay.textContent = codeTemplates.python;
    }


    // ─── BIN Lookup Tool ───
    const binForm = document.getElementById('bin-form');
    const binInput = document.getElementById('bin-input');
    const binBtn = document.getElementById('bin-btn');
    const binLoader = document.getElementById('bin-loader');
    const binResult = document.getElementById('bin-result');

    if (binForm) {
        binForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const bin = binInput.value.trim().replace(/\D/g, '');
            if (bin.length < 6) {
                alert('Please enter at least 6 digits.');
                return;
            }

            binBtn.disabled = true;
            binLoader.classList.remove('hidden');
            binResult.classList.add('hidden');

            try {
                const res = await fetch(`/.netlify/functions/api/bin/${bin}`);
                const data = await res.json();

                if (!res.ok) {
                    throw new Error(data.error || 'Failed to fetch BIN details.');
                }

                document.getElementById('res-bin').textContent = data.bin || bin.substring(0, 6);
                document.getElementById('res-brand').textContent = (data.brand || 'Unknown').toUpperCase();
                document.getElementById('res-type').textContent = (data.type || 'Unknown').toUpperCase();
                document.getElementById('res-category').textContent = (data.category || 'Unknown').toUpperCase();
                document.getElementById('res-bank').textContent = data.bank || 'Unknown';
                document.getElementById('res-country').textContent = `${data.flag || ''} ${data.country_name || 'Unknown'}`;

                binResult.classList.remove('hidden');
            } catch (err) {
                alert(err.message);
            } finally {
                binBtn.disabled = false;
                binLoader.classList.add('hidden');
            }
        });
    }


    // ─── Developer Stats Dashboard ───
    const keyForm = document.getElementById('key-form');
    const keyInput = document.getElementById('key-input');
    const keyBtn = document.getElementById('key-btn');
    const keyLoader = document.getElementById('key-loader');
    const dashboardResult = document.getElementById('dashboard-result');

    if (keyForm) {
        keyForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const key = keyInput.value.trim();
            if (!key) {
                alert('Please enter your API Key.');
                return;
            }

            keyBtn.disabled = true;
            keyLoader.classList.remove('hidden');
            dashboardResult.classList.add('hidden');

            try {
                const res = await fetch('/.netlify/functions/api/stats', {
                    headers: {
                        'X-API-Key': key
                    }
                });
                const data = await res.json();

                if (!res.ok) {
                    throw new Error(data.error || 'Invalid API Key or unauthorized request.');
                }

                const statusBadge = document.getElementById('dash-status');
                statusBadge.textContent = 'Active';
                statusBadge.className = 'badge badge-active';

                document.getElementById('dash-plan').textContent = data.plan_type;
                
                const limit = data.hits_per_day;
                document.getElementById('dash-quota').textContent = `${data.daily_count} / ${limit > 0 ? limit : 'Unlimited'}`;
                document.getElementById('dash-total').textContent = data.total_count;

                const dateObj = new Date(data.created_at);
                document.getElementById('dash-created').textContent = dateObj.toLocaleDateString();

                dashboardResult.classList.remove('hidden');
            } catch (err) {
                alert(err.message);
            } finally {
                keyBtn.disabled = false;
                keyLoader.classList.add('hidden');
            }
        });
    }
});
