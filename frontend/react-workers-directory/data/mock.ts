export type Worker = {
  id: string;
  name: string;
  village: string;
  distanceKm: number;
  phone: string;
  menRate: number;
  womenRate: number;
  available: boolean;
  lat: number;
  lng: number;
};

export const navItems = [
  "Workers Directory",
  "Market",
  "My Bookings",
  "Olive Season",
  "Agro Copilot",
  "Settings",
];

export const workers: Worker[] = [
  {
    id: "w1",
    name: "Ahmad",
    village: "Kfaraka",
    distanceKm: 0.85,
    phone: "+456128",
    menRate: 15,
    womenRate: 10,
    available: true,
    lat: 35.1544,
    lng: 35.7305,
  },
  {
    id: "w2",
    name: "Hassan",
    village: "Batroun",
    distanceKm: 3.2,
    phone: "+456901",
    menRate: 18,
    womenRate: 12,
    available: true,
    lat: 34.2553,
    lng: 35.6581,
  },
];
