import { marketForecasts } from "../data/marketForecasts";
import { marketSummary } from "../data/marketSummary";

const API_BASE_URL = "http://localhost:8000";

export async function getMarketForecasts() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/market-forecasts`);

    if (!response.ok) {
      throw new Error("Failed to fetch market forecasts");
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.warn("Backend unavailable, using mock market forecasts.", error);
    return marketForecasts;
  }
}

export async function getMarketSummary() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/market-summary`);

    if (!response.ok) {
      throw new Error("Failed to fetch market summary");
    }

    return await response.json();
  } catch (error) {
    console.warn("Backend unavailable, using mock market summary.", error);
    return marketSummary;
  }
}