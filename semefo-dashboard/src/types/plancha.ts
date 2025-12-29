export interface Plancha {
    id: number;
    nombre: string;
    descripcion?: string;
    activa: boolean;
    created_at: string;
}

export interface PlanchaCreate {
    nombre: string;
    descripcion?: string;
    activa: boolean;
}
