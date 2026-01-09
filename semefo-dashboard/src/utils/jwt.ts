export function parseJwt(token: string) {
    try {
        if (!token || typeof token !== "string") return null;

        const parts = token.split(".");
        if (parts.length < 2) return null;

        const base64Url = parts[1];
        if (!base64Url) return null;

        // Base64URL -> Base64
        let base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");

        // Padding: base64 debe ser múltiplo de 4
        const pad = base64.length % 4;
        if (pad) base64 += "=".repeat(4 - pad);

        const json = decodeURIComponent(
            Array.prototype.map
                .call(atob(base64), (c: string) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
                .join("")
        );

        return JSON.parse(json);
    } catch {
        return null;
    }
}
