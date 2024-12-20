export type ApiError = {
  detail: string;
  status: number;
};

export class ApiResponse<T> {
  data?: T;
  error?: ApiError;

  constructor(data?: T, error?: ApiError) {
    this.data = data;
    this.error = error;
  }
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080/api/v1';

export async function callAPI<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return new ApiResponse<T>(undefined, {
        detail: data.detail || 'An error occurred',
        status: response.status
      });
    }

    return new ApiResponse<T>(data);
  } catch (error) {
    return new ApiResponse<T>(undefined, {
      detail: error instanceof Error ? error.message : 'An unexpected error occurred',
      status: 500
    });
  }
}
