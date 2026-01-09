import api from "./api";
import type { Plancha } from "../types/plancha";

export async function fetchPlanchas(): Promise<Plancha[]> {
    const { data } = await api.get<Plancha[]>("/dashboard/planchas");
    return data;
}

export async function createPlancha(payload: any) {
    await api.post("/dashboard/planchas", payload);
}

export async function getPlancha(id: number) {
    const { data } = await api.get(`/dashboard/planchas/${id}`);
    return data;
}

export async function updatePlancha(id: number, payload: any) {
    await api.put(`/dashboard/planchas/${id}`, payload);
}

export async function deletePlancha(id: number) {
    await api.delete(`/dashboard/planchas/${id}`);
}
