export function initLocationPicker({
  mapElementId,
  addressInputId,
  latitudeInputId,
  longitudeInputId,
  useMyLocationButtonId,
  defaultCenter = [33.8938, 35.5018], // Beirut
  defaultZoom = 8,
}) {
  const mapEl = document.getElementById(mapElementId);
  const addressInput = document.getElementById(addressInputId);
  const latInput = document.getElementById(latitudeInputId);
  const lngInput = document.getElementById(longitudeInputId);
  const useMyLocationBtn = document.getElementById(useMyLocationButtonId);

  if (!mapEl || !window.L) {
    return {
      getValue: () => ({ address: addressInput?.value || null, latitude: null, longitude: null }),
      setValue: () => {},
      setAddress: () => {},
    };
  }

  const map = window.L.map(mapElementId).setView(defaultCenter, defaultZoom);
  window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  let marker = null;

  function setCoordinates(lat, lng, updateAddress = true) {
    const safeLat = Number(lat);
    const safeLng = Number(lng);
    if (!Number.isFinite(safeLat) || !Number.isFinite(safeLng)) return;

    latInput.value = String(safeLat);
    lngInput.value = String(safeLng);

    if (!marker) {
      marker = window.L.marker([safeLat, safeLng], { draggable: true }).addTo(map);
      marker.on("dragend", async () => {
        const pos = marker.getLatLng();
        setCoordinates(pos.lat, pos.lng, true);
      });
    } else {
      marker.setLatLng([safeLat, safeLng]);
    }

    map.setView([safeLat, safeLng], Math.max(13, map.getZoom()));
    if (updateAddress) {
      reverseGeocode(safeLat, safeLng);
    }
  }

  function setAddress(value) {
    if (!addressInput) return;
    addressInput.value = value || "";
  }

  async function reverseGeocode(lat, lng) {
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lng)}`
      );
      if (!response.ok) return;
      const data = await response.json();
      if (data?.display_name) {
        setAddress(data.display_name);
      }
    } catch {
      // Ignore reverse geocoding failures.
    }
  }

  map.on("click", (event) => {
    setCoordinates(event.latlng.lat, event.latlng.lng, true);
  });

  useMyLocationBtn?.addEventListener("click", () => {
    if (!navigator.geolocation) {
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCoordinates(position.coords.latitude, position.coords.longitude, true);
      },
      () => {
        // User denied or unavailable.
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  });

  const existingLat = Number(latInput?.value);
  const existingLng = Number(lngInput?.value);
  if (Number.isFinite(existingLat) && Number.isFinite(existingLng)) {
    setCoordinates(existingLat, existingLng, false);
  }

  return {
    getValue: () => {
      const latitude = latInput?.value ? Number(latInput.value) : null;
      const longitude = lngInput?.value ? Number(lngInput.value) : null;
      return {
        address: addressInput?.value?.trim() || null,
        latitude: Number.isFinite(latitude) ? latitude : null,
        longitude: Number.isFinite(longitude) ? longitude : null,
      };
    },
    setValue: (latitude, longitude, address = null) => {
      if (latitude === null || longitude === null) return;
      setCoordinates(latitude, longitude, false);
      if (address !== null) setAddress(address);
    },
    setAddress,
  };
}
