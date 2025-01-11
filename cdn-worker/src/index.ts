interface ErrorResponse {
    detail: string
}

export default {
    async fetch(request: Request, env: Env, ctx: ExecutionContext) {
        const url = new URL(request.url)
        const path = url.pathname

        const match = path.match(/^\/images\/([^\/]+)\/([^\/]+)\.([^\/]+)$/)

        if (!match) {
            return jsonError('Not Found', 404)
        }

        const [_, userId, fileHash, _fileExt] = match

        switch (request.method) {
            case 'GET':
                return handleGet(request, env, ctx, userId, fileHash)
            case 'PUT':
                return handlePut(request, env, userId, fileHash)
            case 'DELETE':
                return handleDelete(request, env, userId, fileHash)
            case 'OPTIONS':
                return handleOptions()
            default:
                return jsonError('Method Not Allowed', 405)
        }
    }
}

async function handleGet(request: Request, env: Env, ctx: ExecutionContext, userId: string, fileHash: string) {
    const cacheKey = new Request(request.url)
    const cache = caches.default
    let response = await cache.match(cacheKey)

    if (response) {
        return response
    }

    if (!await has_access(env, userId, fileHash)) {
        response = jsonError('Not Found', 404)
        ctx.waitUntil(cache.put(cacheKey, response.clone()))
        return response
    }

    const s3Url = `https://${env.S3_URL}/${fileHash}`

    const s3Date = new Date().toUTCString()
    const signatureString = `GET\n\n\n${s3Date}\n/plural-images/${fileHash}`
    const signature = await createSignature(signatureString, env.S3_SECRET_ACCESS_KEY)

    const s3Response = await fetch(s3Url, {
        headers: {
            'Host': env.S3_URL,
            'Date': s3Date,
            'Authorization': `AWS ${env.S3_ACCESS_KEY_ID}:${signature}`
        }
    })

    if (!s3Response.ok) {
        return jsonError('Not Found', 404)
    }

    response = new Response(s3Response.body, {
        headers: {
            'Cache-Control': 'public, max-age=31536000',
            'Content-Type': s3Response.headers.get('Content-Type') || 'image/webp',
            'Access-Control-Allow-Origin': '*'
        }
    })

    ctx.waitUntil(cache.put(cacheKey, response.clone()))
    return response
}

async function handlePut(request: Request, env: Env, userId: string, fileHash: string) {
    const authHeader = request.headers.get('Authorization')
    if (!authHeader || authHeader !== `Bearer ${env.API_TOKEN}`) {
        return jsonError('Unauthorized', 401)
    }

    const contentType = request.headers.get('Content-Type')
    if (!contentType?.startsWith('image/')) {
        return jsonError('Invalid Content-Type', 400)
    }

    const contentLength = parseInt(request.headers.get('Content-Length') || '0')
    const MAX_SIZE = 8388608 // 8MB in bytes

    if (contentLength > MAX_SIZE) {
        return jsonError('Payload Too Large', 413)
    }

    if (await has_members(env, fileHash)) {
        if (!await add_access(env, userId, fileHash)) {
            return jsonError('Failed to add user to image', 500)
        }

        return new Response(null, {
            status: 204,
            headers: {
                'Access-Control-Allow-Origin': '*'
            }
        })
    }

    const fileData = await request.arrayBuffer()
    if (fileData.byteLength > MAX_SIZE) {
        return jsonError('Payload Too Large', 413)
    }

    const s3Date = new Date().toUTCString()
    const contentMD5 = await calculateMD5(fileData)
    const signatureString = `PUT\n${contentMD5}\n${contentType}\n${s3Date}\n/plural-images/${fileHash}`
    const signature = await createSignature(signatureString, env.S3_SECRET_ACCESS_KEY)

    const s3Response = await fetch(
        `https://${env.S3_URL}/${fileHash}`,
        {
            method: 'PUT',
            headers: {
                'Host': env.S3_URL,
                'Date': s3Date,
                'Content-Type': contentType,
                'Content-MD5': contentMD5,
                'Authorization': `AWS ${env.S3_ACCESS_KEY_ID}:${signature}`},
            body: fileData
        }
    )

    if (!s3Response.ok) {
        return jsonError('Failed to upload image', 500)
    }

    await add_access(env, userId, fileHash)

    const cacheKey = new Request(request.url)
    const cache = caches.default
    await cache.delete(cacheKey)

    return new Response(null, {
        status: 204,
        headers: {
            'Access-Control-Allow-Origin': '*'
        }
    })
}

async function handleDelete(request: Request, env: Env, userId: string, fileHash: string) {
    const authHeader = request.headers.get('Authorization')
    if (!authHeader || authHeader !== `Bearer ${env.API_TOKEN}`) {
        return jsonError('Unauthorized', 401)
    }

    if (!await has_access(env, userId, fileHash)) {
        return jsonError('Not Found', 404)
    }

    await remove_access(env, userId, fileHash)

    if (!await has_members(env, fileHash)) {
        const s3Date = new Date().toUTCString()
        const signatureString = `DELETE\n\n\n${s3Date}\n/plural-images/${fileHash}`
        const signature = await createSignature(signatureString, env.S3_SECRET_ACCESS_KEY)

        const s3Response = await fetch(
            `https://${env.S3_URL}/${fileHash}`,
            {
                method: 'DELETE',
                headers: {
                    'Host': env.S3_URL,
                    'Date': s3Date,
                    'Authorization': `AWS ${env.S3_ACCESS_KEY_ID}:${signature}`
                }
            }
        )

        if (!s3Response.ok) {
            return jsonError('Failed to delete image', 500)
        }
    }

    const cacheKey = new Request(request.url)
    const cache = caches.default
    await cache.delete(cacheKey)

    return new Response(null, {
        status: 204,
        headers: {
            'Access-Control-Allow-Origin': '*'
        }
    })
}


function handleOptions() {
    return new Response(null, {
        headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '86400',
        }
    })
}

async function createSignature(stringToSign: string, secretKey: string): Promise<string> {
    const encoder = new TextEncoder()
    const keyData = encoder.encode(secretKey)
    const messageData = encoder.encode(stringToSign)

    const key = await crypto.subtle.importKey(
        'raw',
        keyData,
        { name: 'HMAC', hash: 'SHA-1' },
        false,
        ['sign']
    )

    const signature = await crypto.subtle.sign(
        'HMAC',
        key,
        messageData
    )

    return btoa(String.fromCharCode(...new Uint8Array(signature)))
}

async function calculateMD5(data: ArrayBuffer): Promise<string> {
    const hash = await crypto.subtle.digest('MD5', data)
    return btoa(String.fromCharCode(...new Uint8Array(hash)))
}

function jsonError(message: string, status: number): Response {
    return new Response(
        JSON.stringify({ detail: message } as ErrorResponse),
        {
            status,
            headers: {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            }
        }
    )
}

async function has_access(env: Env, userId: string, fileHash: string): Promise<boolean> {
    const response = await fetch(`${env.UPSTASH_URL}/sismember/${fileHash}/${userId}`, {
        headers: {
            'Authorization': `Bearer ${env.UPSTASH_TOKEN}`
        }
    })
    
    if (!response.ok) {
        return false
    }

    return (
        await response.json() as { result: number }
    ).result === 1
}

async function add_access(env: Env, userId: string, fileHash: string): Promise<boolean> {
    const response = await fetch(`${env.UPSTASH_URL}/sadd/${fileHash}/${userId}`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${env.UPSTASH_TOKEN}`
        }
    })

    return response.ok
}

async function remove_access(env: Env, userId: string, fileHash: string): Promise<boolean> {
    const response = await fetch(`${env.UPSTASH_URL}/srem/${fileHash}/${userId}`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${env.UPSTASH_TOKEN}`
        }
    })

    return response.ok
}

async function has_members(env: Env, fileHash: string): Promise<boolean> {
    const response = await fetch(`${env.UPSTASH_URL}/scard/${fileHash}`, {
        headers: {
            'Authorization': `Bearer ${env.UPSTASH_TOKEN}`
        }
    })

    if (!response.ok) {
        return false
    }

    return (
        await response.json() as { result: number }
    ).result > 0
}
