import { chromium } from "playwright";

const BASE_URL = process.env.BASE_URL || "http://127.0.0.1:4173";

const counters = {
  workersGet: 0,
  seasonsGet: 0,
  weatherGet: 0,
  bookingsPost: 0,
  availabilityPatch: 0,
};

const sampleWorkers = [
  {
    id: "worker-1",
    name: "joseph worker",
    village: "Lille",
    address: "Rue Test",
    phone: "+33100000000",
    available: true,
    men_count: 3,
    women_count: 2,
    remaining_men_count: 2,
    remaining_women_count: 1,
    rate_type: "day",
    men_rate_value: 25,
    women_rate_value: 20,
    available_dates: ["2026-04-25"],
    availability_windows: [{ work_date: "2026-04-25", slot_type: "full_day" }],
    overtime_open: true,
    overtime_note: "Can do overtime",
    distance_km: 4.2,
    latitude: 50.6292,
    longitude: 3.0573,
  },
];

function sessionFor(role) {
  return {
    access_token: "test-token",
    user: {
      id: `user-${role}`,
      role,
      full_name: role === "farmer" ? "Farmer Test" : "Worker Test",
      latitude: null,
      longitude: null,
    },
  };
}

function expect(condition, message) {
  if (!condition) throw new Error(message);
}

function addLeafletStub(page) {
  return page.addInitScript(() => {
    if (window.L) return;

    class DummyLayer {
      addTo() {
        return this;
      }
      clearLayers() {
        return this;
      }
      bindTooltip() {
        return this;
      }
      bindPopup() {
        return this;
      }
      on() {
        return this;
      }
      setLatLng(latlng) {
        this._latlng = latlng;
        return this;
      }
      getLatLng() {
        return { lat: this._latlng?.[0] || 0, lng: this._latlng?.[1] || 0 };
      }
      openTooltip() {
        return this;
      }
      closeTooltip() {
        return this;
      }
      openPopup() {
        return this;
      }
    }

    window.L = {
      map() {
        return {
          setView() {
            return this;
          },
          fitBounds() {
            return this;
          },
          getZoom() {
            return 13;
          },
        };
      },
      tileLayer() {
        return new DummyLayer();
      },
      layerGroup() {
        return new DummyLayer();
      },
      marker() {
        return new DummyLayer();
      },
      divIcon(config) {
        return config;
      },
      control() {
        return {
          onAdd: null,
          addTo(map) {
            if (typeof this.onAdd === "function") this.onAdd(map);
            return this;
          },
        };
      },
      DomUtil: {
        create(tag, className) {
          const el = document.createElement(tag);
          if (className) el.className = className;
          return el;
        },
      },
      DomEvent: {
        disableClickPropagation() {},
        disableScrollPropagation() {},
      },
    };
  });
}

async function setupRoutes(page) {
  await page.route("**/*", async (route) => {
    const req = route.request();
    const url = new URL(req.url());

    if (url.origin === "http://127.0.0.1:8000") {
      if (url.pathname === "/olive-seasons/mine" && req.method() === "GET") {
        counters.seasonsGet += 1;
        return route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
      }
      if (url.pathname === "/workers" && req.method() === "GET") {
        counters.workersGet += 1;
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(sampleWorkers),
        });
      }
      if (url.pathname === "/workers/worker-1/bookings" && req.method() === "POST") {
        counters.bookingsPost += 1;
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([{ id: "booking-1" }]),
        });
      }
      if (url.pathname === "/workers/worker-1/availability" && req.method() === "PATCH") {
        counters.availabilityPatch += 1;
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ ok: true }),
        });
      }

      return route.fulfill({ status: 404, contentType: "application/json", body: '{"detail":"not found"}' });
    }

    if (url.origin === "https://api.open-meteo.com") {
      counters.weatherGet += 1;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          current: {
            temperature_2m: 20.5,
            apparent_temperature: 21.1,
            weather_code: 1,
            wind_speed_10m: 9.1,
          },
          current_units: {
            temperature_2m: "C",
            wind_speed_10m: "km/h",
          },
        }),
      });
    }

    return route.continue();
  });
}

async function runFarmerChecks(browser) {
  const context = await browser.newContext({
    permissions: ["geolocation"],
    geolocation: { latitude: 50.6292, longitude: 3.0573 },
  });
  const page = await context.newPage();

  await addLeafletStub(page);
  await page.addInitScript((session) => {
    localStorage.setItem("worker_radar_session", JSON.stringify(session));
    localStorage.removeItem("workers_advanced_filters_open_v1");
  }, sessionFor("farmer"));
  await setupRoutes(page);

  await page.goto(`${BASE_URL}/workers.html`, { waitUntil: "networkidle" });

  const details = page.locator("#advanced-filters");
  await expect(await details.count() === 1, "Advanced filters control missing");
  await expect(!(await details.evaluate((el) => el.open)), "Advanced filters should start collapsed");

  await details.locator("summary").click();
  await page.waitForTimeout(120);
  await expect(await details.evaluate((el) => el.open), "Advanced filters did not open on click");

  await page.locator('input[name="max_distance_km"]').fill("25");
  await expect(
    (await page.locator("#advanced-filters-count").textContent())?.includes("active"),
    "Advanced active badge was not updated"
  );

  await page.locator("#use-my-location-btn").click();
  await page.waitForFunction(
    () => {
      const input = document.querySelector('input[name="near_latitude"]');
      return Boolean(input && String(input.value || "").trim());
    },
    null,
    { timeout: 5000 }
  );
  await expect((await page.locator('input[name="near_latitude"]').inputValue()) !== "", "Use My Location did not set latitude");

  await page.locator('button[type="submit"]').click();
  await page.waitForTimeout(200);

  await page.locator('[data-open-worker="worker-1"]').first().click();
  await expect(!(await page.locator("#worker-detail-panel").evaluate((el) => el.hidden)), "Worker detail panel did not open");

  const panel = page.locator("#worker-detail-panel");
  await panel.locator('input[name="work_date"]').first().fill("2026-04-25");
  await panel.locator('input[name="requested_men"]').first().fill("1");
  await panel.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(250);

  await page.locator("#worker-detail-close").click();
  await page.waitForTimeout(120);
  await expect(await page.locator("#worker-detail-panel").evaluate((el) => el.hidden), "Worker detail panel did not close");

  // Persisted state check
  await details.locator("summary").click(); // close
  await page.waitForTimeout(120);
  await page.reload({ waitUntil: "networkidle" });
  await expect(!(await page.locator("#advanced-filters").evaluate((el) => el.open)), "Advanced filters open/close state did not persist");

  await context.close();
}

async function runWorkerChecks(browser) {
  const context = await browser.newContext();
  const page = await context.newPage();

  await addLeafletStub(page);
  await page.addInitScript((session) => {
    localStorage.setItem("worker_radar_session", JSON.stringify(session));
  }, sessionFor("worker"));
  await setupRoutes(page);

  await page.goto(`${BASE_URL}/workers.html`, { waitUntil: "networkidle" });

  const availabilityBtn = page.locator('button[data-id="worker-1"]').first();
  await expect(await availabilityBtn.count() === 1, "Worker availability toggle button missing");
  await availabilityBtn.click();
  await page.waitForTimeout(220);

  await context.close();
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    await runFarmerChecks(browser);
    await runWorkerChecks(browser);

    expect(counters.workersGet > 0, "Workers API was not called");
    expect(counters.weatherGet > 0, "Weather API was not called");
    expect(counters.availabilityPatch > 0, "Availability PATCH was not called");
    expect(counters.bookingsPost > 0, "Booking POST was not called");

    console.log("WORKERS_SMOKE_OK", JSON.stringify(counters));
  } catch (error) {
    console.error("WORKERS_SMOKE_FAIL", error?.message || error);
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
