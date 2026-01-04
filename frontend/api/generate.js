export default async function handler(req, res) {
    // CORS Handling
    res.setHeader('Access-Control-Allow-Credentials', true);
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
    res.setHeader(
        'Access-Control-Allow-Headers',
        'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version'
    );

    if (req.method === 'OPTIONS') {
        res.status(200).end();
        return;
    }

    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Method not allowed' });
    }

    const backendUrl = process.env.VITE_BACKEND_URL;
    const hfToken = process.env.HF_TOKEN;

    if (!backendUrl) {
        return res.status(500).json({ error: 'Backend URL not configured' });
    }

    try {
        const response = await fetch(`${backendUrl}/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(hfToken ? { 'Authorization': `Bearer ${hfToken}` } : {}),
            },
            body: JSON.stringify(req.body),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            return res.status(response.status).json(errorData);
        }

        const data = await response.json();
        return res.status(200).json(data);

    } catch (error) {
        console.error('Proxy error:', error);
        return res.status(500).json({ error: 'Failed to connect to backend', details: error.message });
    }
}
