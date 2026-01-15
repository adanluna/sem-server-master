export type ServiceClient = {
    id: number;
    client_id: string;
    roles: string;
    activo: boolean;
    allowed_ips?: string | null;
    last_used_at?: string | null;
    created_at: string;
};

export type ServiceClientCreate = {
    client_id: string;
    roles?: string;
    activo?: boolean;
    allowed_ips?: string | null;

    // opcional: si lo mandas, ese será el token
    token?: string | null;
};

export type ServiceClientUpdate = {
    roles?: string;
    activo?: boolean;
    allowed_ips?: string | null;
};

export type ServiceClientCreatedResponse = {
    service_client: ServiceClient;
    token: string; // solo en create/rotate
};
