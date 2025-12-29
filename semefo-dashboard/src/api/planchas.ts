import api from "./api";
import type { Plancha, PlanchaCreate } from "../types/plancha";

export async function fetchPlanchas(): Promise<Plancha[]> {
    const { data } = await api.get<Plancha[]>("/planchas");
    return data;
}

export async function createPlancha(payload: PlanchaCreate) {
    await api.post("/planchas", payload);
}

export async function updatePlancha(id: number, payload: PlanchaCreate) {
    await api.put(`/planchas/${id}`, payload);
}

export async function deletePlancha(id: number) {
    await api.delete(`/planchas/${id}`);
}
