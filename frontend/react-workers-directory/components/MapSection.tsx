"use client";

import { MapContainer, Marker, Popup, TileLayer, ZoomControl } from "react-leaflet";
import type { Worker } from "../data/mock";
import "leaflet/dist/leaflet.css";

type MapSectionProps = {
  workers: Worker[];
};

export function MapSection({ workers }: MapSectionProps) {
  const center = workers.length ? [workers[0].lat, workers[0].lng] : [35.15, 35.73];

  return (
    <section className="glass-soft overflow-hidden p-3">
      <h3 className="mb-3 text-3xl font-semibold text-[#2a3c20]">Map</h3>
      <div className="h-[360px] overflow-hidden rounded-xl shadow-md">
        <MapContainer center={center as [number, number]} zoom={11} zoomControl={false} className="h-full w-full">
          <ZoomControl position="topright" />
          <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {workers.map((worker) => (
            <Marker key={worker.id} position={[worker.lat, worker.lng]}>
              <Popup>
                <div className="space-y-1 text-sm">
                  <p className="font-semibold">{worker.name}</p>
                  <p>M: 1 W: 1</p>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </section>
  );
}
