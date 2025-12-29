import api from "./api";
import type { LoginResponse } from "../types/auth";

export async function loginDashboard(
    username: string,
    password: string
): Promise<LoginResponse> {
    const { data } = await api.post<LoginResponse>(
        "/dashboard/login",
        { username, password }
    );
    return data;
}
