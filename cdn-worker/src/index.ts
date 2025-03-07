interface ErrorResponse {
    detail: string
}

interface RequestProps {
    method: string
    headers: Headers
    body?: ArrayBuffer
}

interface CDNRequest {
    request: Request
    env: Env
    ctx: ExecutionContext
    userId: string
    fileHash: string
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

        const cdnRequest = {
            request,
            env,
            ctx,
            userId,
            fileHash
        } as CDNRequest

        let response

        switch (request.method) {
            case 'GET':
                response = await handleGet(cdnRequest)
                break
            case 'HEAD':
                response = await handleHead(cdnRequest)
                break
            case 'PUT':
                response = await handlePut(cdnRequest)
                break
            case 'DELETE':
                response = await handleDelete(cdnRequest)
                break
            case 'OPTIONS':
                return handleOptions()
            default:
                return jsonError('Method Not Allowed', 405)
        }

        return response
    }
}

async function handleGet(cdnRequest: CDNRequest): Promise<Response> {
    const cacheKey = new Request(cdnRequest.request.url)

    let response = await caches.default.match(cacheKey)

    if (response) {
        return response
    }

    if (!await has_access(cdnRequest)) {
        response = jsonError('Not Found', 404)
        cdnRequest.ctx.waitUntil(caches.default.put(cacheKey, response.clone()))
        return response
    }

    const s3Response = await s3_fetch('GET', cdnRequest)

    if (!s3Response.ok) {
        return jsonError('Not Found', 404)
    }

    response = new Response(s3Response.body, {
        headers: {
            'Cache-Control': 'public, max-age=31536000',
            'Content-Type': s3Response.headers.get('Content-Type') || 'image/webp',
            'Content-Length': s3Response.headers.get('Content-Length') || '0',
            'Access-Control-Allow-Origin': '*'
        }
    })

    cdnRequest.ctx.waitUntil(caches.default.put(cacheKey, response.clone()))
    return response
}

async function handleHead(cdnRequest: CDNRequest): Promise<Response> {
    const response = await handleGet(cdnRequest)

    return new Response(null, {
        status: response.status,
        headers: response.headers
    })
}

async function handlePut(cdnRequest: CDNRequest): Promise<Response> {
    const authHeader = cdnRequest.request.headers.get('Authorization')

    if (!authHeader || authHeader !== `Bearer ${cdnRequest.env.UPLOAD_TOKEN}`) {
        return jsonError('Unauthorized', 401)
    }

    const contentType = cdnRequest.request.headers.get('Content-Type')
    if (!contentType?.startsWith('image/')) {
        return jsonError('Invalid Content-Type', 400)
    }

    const contentLength = parseInt(cdnRequest.request.headers.get('Content-Length') || '0')

    const MAX_SIZE = 4_194_304 // 4MB in bytes

    if (contentLength > MAX_SIZE) {
        return jsonError('Payload Too Large', 413)
    }

    if (await has_members(cdnRequest)) {
        if (!await add_access(cdnRequest)) {
            return jsonError('Failed to add user to image', 500)
        }

        return new Response(null, {
            status: 204,
            headers: {
                'Access-Control-Allow-Origin': '*'
            }
        })
    }

    const fileData = await cdnRequest.request.arrayBuffer()
    if (fileData.byteLength > MAX_SIZE) {
        return jsonError('Payload Too Large', 413)
    }

    const s3Response = await s3_fetch('PUT', cdnRequest, fileData)

    if (!s3Response.ok) {
        return jsonError(`Failed to upload image: ${await s3Response.text()}`, 500)
    }

    await add_access(cdnRequest)

    await caches.default.delete(new Request(cdnRequest.request.url))

    return new Response(null, {
        status: 204,
        headers: {
            'Access-Control-Allow-Origin': '*'
        }
    })
}

async function handleDelete(cdnRequest: CDNRequest): Promise<Response> {
    const authHeader = cdnRequest.request.headers.get('Authorization')

    if (!authHeader || authHeader !== `Bearer ${cdnRequest.env.UPLOAD_TOKEN}`) {
        return jsonError('Unauthorized', 401)
    }

    if (!await has_access(cdnRequest)) {
        return jsonError('Not Found', 404)
    }

    await remove_access(cdnRequest)

    if (!await has_members(cdnRequest)) {
        const s3Response = await s3_fetch('DELETE', cdnRequest)

        if (!s3Response.ok) {
            return jsonError(`Failed to upload image: ${await s3Response.text()}`, 500)
        }
    }

    await fetch(
        `https://api.cloudflare.com/client/v4/zones/${cdnRequest.env.CLOUDFLARE_ZONE_ID}/purge_cache`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${cdnRequest.env.CLOUDFLARE_API_TOKEN}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ "files": [cdnRequest.request.url] })
    })

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
            'Access-Control-Allow-Methods': 'GET, PUT, DELETE, HEAD, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Content-Length, Authorization',
            'Access-Control-Max-Age': '86400',
        }
    })
}

async function s3_fetch(
    method: string,
    cdnRequest: CDNRequest,
    body: ArrayBuffer | null = null
): Promise<Response> {
    const url = `https://${cdnRequest.env.S3_URL}/${cdnRequest.env.S3_BUCKET}/${cdnRequest.fileHash}`

    return fetch(
        url,
        await createSignedRequest(
            method,
            url,
            body,
            cdnRequest.env
        )
    )
}

// ? i don't understand most of this, i severely dislike s3
async function createSignedRequest(
    method: string,
    url: string,
    body: ArrayBuffer | null,
    env: Env
): Promise<RequestProps> {
    const parsedUrl = new URL(url)

    const sha256 = async (data: ArrayBuffer): Promise<string> => {
        return hexEncode(await crypto.subtle.digest('SHA-256', data))
    }

    const hmac = async (key: ArrayBuffer, message: string): Promise<ArrayBuffer> => {
        const encoder = new TextEncoder()
        return await crypto.subtle.sign(
            'HMAC',
            await crypto.subtle.importKey(
                'raw',
                key,
                { name: 'HMAC', hash: 'SHA-256' },
                false,
                ['sign']),
            encoder.encode(message)
        )
    }

    const hexEncode = (buffer: ArrayBuffer): string => {
        return [...new Uint8Array(buffer)]
            .map(b => b.toString(16).padStart(2, '0'))
            .join('')
    }

    const now = new Date()
    const amzDate = now.toISOString().replace(/[:-]|\.\d{3}/g, '')
    const dateStamp = now.toISOString().slice(0, 10).replace(/-/g, '')

    const payloadHash = body ? await sha256(body) : await sha256(new ArrayBuffer(0))

    const signedHeaders = 'host;x-amz-content-sha256;x-amz-date'

    const canonicalRequest = [
        method,
        parsedUrl.pathname,
        parsedUrl.searchParams.toString() || '',
        [
            `host:${parsedUrl.hostname}`,
            `x-amz-content-sha256:${payloadHash}`,
            `x-amz-date:${amzDate}`,
        ].join('\n') + '\n',
        signedHeaders,
        payloadHash
    ].join('\n')

    const credentialScope = `${dateStamp}/${env.S3_REGION}/s3/aws4_request`
    const stringToSign = [
        'AWS4-HMAC-SHA256',
        amzDate,
        credentialScope,
        await sha256(new TextEncoder().encode(canonicalRequest))
    ].join('\n')


    // ? i miss elixir
    const signatureKey = await hmac(
        await hmac(
            await hmac(
                await hmac(
                    new TextEncoder().encode('AWS4' + env.S3_SECRET_ACCESS_KEY),
                    dateStamp),
                env.S3_REGION),
            's3'),
        'aws4_request'
    )

    const signature = hexEncode(await hmac(signatureKey, stringToSign))

    return {
        method,
        headers: new Headers({
            'Host': parsedUrl.hostname,
            'x-amz-content-sha256': payloadHash,
            'x-amz-date': amzDate,
            'Authorization': [
                `AWS4-HMAC-SHA256 Credential=${env.S3_ACCESS_KEY_ID}/${credentialScope},`,
                `SignedHeaders=${signedHeaders},`,
                `Signature=${signature}`
            ].join(''),
            'Content-Type': 'image/webp'}),
        body: body || undefined
    }
}

function jsonError(message: string, status: number): Response {
    const response = JSON.stringify({ detail: message } as ErrorResponse)
    return new Response(
        response, {
        status,
        headers: {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json',
            'Content-Length': `${response.length}`
        }
    })
}

async function has_access(cdnRequest: CDNRequest): Promise<boolean> {
    return (await fetch(
        `${cdnRequest.env.API_URL}/__redis/SISMEMBER/avatar:${cdnRequest.fileHash}/${cdnRequest.userId}`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${cdnRequest.env.UPLOAD_TOKEN}`}}
    )).ok
}

async function add_access(cdnRequest: CDNRequest): Promise<boolean> {
    return (await fetch(
        `${cdnRequest.env.API_URL}/__redis/SADD/avatar:${cdnRequest.fileHash}/${cdnRequest.userId}`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${cdnRequest.env.UPLOAD_TOKEN}`}}
    )).ok
}

async function remove_access(cdnRequest: CDNRequest): Promise<boolean> {
    return (await fetch(
        `${cdnRequest.env.API_URL}/__redis/SREM/avatar:${cdnRequest.fileHash}/${cdnRequest.userId}`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${cdnRequest.env.UPLOAD_TOKEN}`}}
    )).ok
}

async function has_members(cdnRequest: CDNRequest): Promise<boolean> {
    return (await fetch(
        `${cdnRequest.env.API_URL}/__redis/SCARD/avatar:${cdnRequest.fileHash}/None`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${cdnRequest.env.UPLOAD_TOKEN}`}}
    )).status === 200
}
