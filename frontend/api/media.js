export default async function handler(req, res) {
    // CORS Handling
    res.setHeader('Access-Control-Allow-Credentials', true);
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS');
    res.setHeader(
        'Access-Control-Allow-Headers',
        'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version'
    );

    if (req.method === 'OPTIONS') {
        res.status(200).end();
        return;
    }

    const { path } = req.query;

    if (!path) {
        return res.status(400).json({ error: 'Missing path parameter' });
    }

    const backendUrl = process.env.VITE_BACKEND_URL;
    const hfToken = process.env.HF_TOKEN;

    if (!backendUrl) {
        return res.status(500).json({ error: 'Backend URL not configured' });
    }

    // Ensure path starts with /
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    const targetUrl = `${backendUrl}${cleanPath}`;

    try {
        const response = await fetch(targetUrl, {
            headers: {
                ...(hfToken ? { 'Authorization': `Bearer ${hfToken}` } : {}),
            },
        });

        if (!response.ok) {
            console.error(`Media proxy error: ${response.status} ${response.statusText} for ${targetUrl}`);
            return res.status(response.status).send('Failed to fetch media');
        }

        // Forward content headers
        const contentType = response.headers.get('content-type');
        const contentLength = response.headers.get('content-length');

        if (contentType) res.setHeader('Content-Type', contentType);
        if (contentLength) res.setHeader('Content-Length', contentLength);

        // Stream the response body
        // Note: Vercel functions (Node.js) might need buffer if not using edge runtime
        const arrayBuffer = await response.arrayBuffer();
        const buffer = Buffer.from(arrayBuffer);

        res.status(200).send(buffer);

    } catch (error) {
        console.error('Media proxy exception:', error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
}
