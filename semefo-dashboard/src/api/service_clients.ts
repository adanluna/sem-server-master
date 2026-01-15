import api from "./api";
import type {
    ServiceClient,
    ServiceClientCreate,
    ServiceClientUpdate,
    ServiceClientCreatedResponse
} from "../types/service_client";

export async function listServiceClients(params?: { q?: string; solo_activos?: boolean }) {
    const { data } = await api.get<ServiceClient[]>("/dashboard/service-clients", { params });
    return data;
}

export async function getServiceClient(id: number) {
    const { data } = await api.get<ServiceClient>(`/dashboard/service-clients/${id}`);
    return data;
}

export async function createServiceClient(payload: ServiceClientCreate) {
    const { data } = await api.post<ServiceClientCreatedResponse>("/dashboard/service-clients", payload);
    return data;
}

export async function updateServiceClient(id: number, payload: ServiceClientUpdate) {
    const { data } = await api.put<ServiceClient>(`/dashboard/service-clients/${id}`, payload);
    return data;
}

export async function rotateServiceClientToken(id: number) {
    const { data } = await api.post<ServiceClientCreatedResponse>(`/dashboard/service-clients/${id}/rotar-token`);
    return data;
}

export async function activateServiceClient(id: number) {
    const { data } = await api.post<ServiceClient>(`/dashboard/service-clients/${id}/activar`);
    return data;
}

export async function deactivateServiceClient(id: number) {
    const { data } = await api.post<ServiceClient>(`/dashboard/service-clients/${id}/desactivar`);
    return data;
}

// Yo NO recomiendo delete hard en gobierno, pero si lo dejaste:
export async function deleteServiceClient(id: number) {
    const { data } = await api.delete(`/dashboard/service-clients/${id}`);
    return data;
}
