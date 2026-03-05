import axios from "axios";

const API = axios.create({ baseURL: "http://localhost:8000" });

export const getHealth = () => API.get("/health");
export const getEvents = () => API.get("/events");
export const getStatus = () => API.get("/status");
