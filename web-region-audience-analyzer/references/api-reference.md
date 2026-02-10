# API Reference

## IP Geolocation: ip-api.com

**Endpoint**: `GET http://ip-api.com/json/{ip}`

**Parameters**:
- `fields`: Comma-separated list of fields to return.
  - Recommended: `status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query`

**Response Example**:
```json
{
  "status": "success",
  "country": "United States",
  "countryCode": "US",
  "region": "CA",
  "regionName": "California",
  "city": "San Francisco",
  "zip": "94107",
  "lat": 37.7749,
  "lon": -122.4194,
  "timezone": "America/Los_Angeles",
  "isp": "Google LLC",
  "org": "Google Cloud",
  "as": "AS15169 Google LLC",
  "query": "8.8.8.8"
}
```

**Rate Limits**:
- Free: 45 requests per minute per IP address.
- HTTP only (HTTPS requires Pro).

**Error Handling**:
- Check `status` field. If "fail", `message` contains the error reason.

## Language Detection: NLP Cloud

**Endpoint**: `POST https://api.nlpcloud.io/v1/gpu/lang-detect`

**Headers**:
- `Authorization`: `Token <your_token>`
- `Content-Type`: `application/json`

**Body**:
```json
{
  "text": "Text to analyze..."
}
```

**Response Example**:
```json
{
  "languages": [
    {
      "language": "en",
      "score": 0.98
    },
    {
      "language": "fr",
      "score": 0.02
    }
  ]
}
```

**Notes**:
- Requires an API token.
- GPU-accelerated models provide higher accuracy than offline libraries.
