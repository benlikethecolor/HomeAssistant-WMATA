import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import test from "node:test";
import { Window } from "happy-dom";

const source = readFileSync(
  new URL(
    "../custom_components/wmata/www/wmata-station-card.js",
    import.meta.url,
  ),
  "utf8",
);
const sample = [
  {
    line: "BL",
    destination: "Franconia-Springfield",
    destination_code: "J03",
    minutes: 3,
    status: "predicted",
    group: "1",
    direction: "Westbound",
    cars: "8",
  },
  {
    line: "SV",
    destination: "Ashburn",
    destination_code: "N12",
    minutes: 7,
    status: "predicted",
    group: "1",
  },
  {
    line: "BL",
    destination: "Downtown Largo",
    destination_code: "G05",
    minutes: 12,
    status: "predicted",
    group: "2",
  },
];
function fixture(t, arrivals = sample, config = {}) {
  const window = new Window({ url: "http://localhost/" });
  window.eval(source);
  const card = window.document.createElement("wmata-station-card");
  const hass = {
    states: {
      "sensor.wmata_g01_arrivals": {
        state: arrivals.length ? "3" : "unknown",
        attributes: {
          schema_version: 1,
          board_type: "station",
          station_name: "Benning Road",
          service_type: "train",
          arrivals,
          updated_at: new Date().toISOString(),
          poll_interval: 30,
        },
      },
    },
  };
  card.setConfig({ entity: "sensor.wmata_g01_arrivals", ...config });
  card.hass = hass;
  window.document.body.append(card);
  t.after(async () => {
    card.remove();
    await window.happyDOM.close();
  });
  return { window, card, hass, root: card.shadowRoot };
}

test("station renders one combined board and supports row limits", (t) => {
  const { root } = fixture(t, sample, { max_rows: 2 });
  assert.equal(root.querySelectorAll(".arrival").length, 2);
  assert.match(root.querySelector(".title").textContent, /Benning Road/);
  assert.match(root.querySelector(".footer").textContent, /2 of 3 arrivals/);
  assert.match(root.querySelector(".live").textContent, /LIVE/);
});

test("line and destination filters combine and remain selected after updates", (t) => {
  const { root, card, hass, window } = fixture(t);
  [...root.querySelectorAll(".chip")]
    .find((c) => c.textContent === "Blue")
    .click();
  assert.equal(root.querySelectorAll(".arrival").length, 2);
  const select = root.querySelector("select");
  select.value = "J03";
  select.dispatchEvent(new window.Event("change"));
  assert.equal(root.querySelectorAll(".arrival").length, 1);
  const state = hass.states["sensor.wmata_g01_arrivals"];
  card.hass = {
    states: {
      "sensor.wmata_g01_arrivals": {
        ...state,
        attributes: { ...state.attributes, arrivals: sample.slice(1) },
      },
    },
  };
  assert.equal(root.querySelector("select").value, "J03");
  assert.match(root.querySelector(".message").textContent, /No arrivals match/);
});

test("missing estimates are distinct from arriving and boarding", (t) => {
  const arrivals = [
    { ...sample[0], minutes: 0, status: "boarding" },
    { ...sample[1], minutes: 0, status: "arriving" },
    { ...sample[2], minutes: null, status: "delayed" },
    { ...sample[2], minutes: null, status: "unknown" },
  ];
  const { root } = fixture(t, arrivals);
  assert.deepEqual(
    [...root.querySelectorAll(".eta")].map((n) => n.textContent),
    ["Boarding", "Arriving", "Delayed", "No estimate"],
  );
});

test("empty predictions are not reported as an outage", (t) => {
  const { root } = fixture(t, []);
  assert.match(
    root.querySelector(".message").textContent,
    /No upcoming arrivals/,
  );
  assert.equal(root.querySelector(".live").dataset.stale, "false");
});

test("unavailable state hides stale arrivals and stale timestamps are labeled", (t) => {
  const { card, hass, root } = fixture(t);
  const state = hass.states["sensor.wmata_g01_arrivals"];
  card.hass = {
    states: {
      "sensor.wmata_g01_arrivals": {
        ...state,
        attributes: { ...state.attributes, updated_at: "2000-01-01T00:00:00Z" },
      },
    },
  };
  assert.match(root.querySelector(".live").textContent, /STALE/);
  card.hass = {
    states: { "sensor.wmata_g01_arrivals": { ...state, state: "unavailable" } },
  };
  assert.equal(root.querySelectorAll(".arrival").length, 0);
  assert.match(root.querySelector(".message").textContent, /unavailable/);
});

test("untrusted API text and titles cannot inject markup", (t) => {
  const unsafe = '<img src=x onerror="window.pwned=true">';
  const { root, window } = fixture(t, [{ ...sample[0], destination: unsafe }], {
    title: unsafe,
  });
  assert.equal(root.querySelectorAll("img").length, 0);
  assert.equal(root.querySelector(".destination").textContent, unsafe);
  assert.equal(window.pwned, undefined);
});

test("bus routes and direction text render using the same card", (t) => {
  const { card, hass, root } = fixture(t, [
    {
      route: "D34",
      destination: "East to Union Station",
      minutes: 4,
      vehicle_id: "1234",
    },
  ]);
  const state = hass.states["sensor.wmata_g01_arrivals"];
  card.hass = {
    states: {
      "sensor.wmata_g01_arrivals": {
        ...state,
        attributes: { ...state.attributes, service_type: "bus" },
      },
    },
  };
  assert.equal(root.querySelector(".badge").textContent, "D34");
  assert.match(root.querySelector(".chips").textContent, /All routes/);
});

test("title opens the HA entity details and visual editor emits valid configuration", (t) => {
  const { card, root, window, hass } = fixture(t);
  let detail;
  card.addEventListener("hass-more-info", (event) => (detail = event.detail));
  root.querySelector(".title").click();
  assert.equal(detail.entityId, "sensor.wmata_g01_arrivals");
  const editor = window.document.createElement("wmata-station-card-editor");
  editor.setConfig({
    type: "custom:wmata-station-card",
    entity: "sensor.wmata_g01_arrivals",
  });
  editor.hass = hass;
  let config;
  editor.addEventListener(
    "config-changed",
    (event) => (config = event.detail.config),
  );
  editor.querySelector("ha-form").dispatchEvent(
    new window.CustomEvent("value-changed", {
      detail: { value: { max_rows: 5 } },
      bubbles: true,
    }),
  );
  assert.equal(config.max_rows, 5);
  assert.equal(config.type, "custom:wmata-station-card");
  assert.throws(
    () => card.setConfig({ entity: "sensor.foo", max_rows: 0 }),
    /max_rows/,
  );
  assert.throws(
    () => card.setConfig({ entity: "sensor.foo", lines: "BL" }),
    /list/,
  );
});

const mapData = {
  paths: [
    {
      line: "SV",
      points: [
        [100, 300],
        [200, 400],
      ],
    },
  ],
  trains: [
    {
      id: "1",
      line: "SV",
      destination: "Ashburn",
      track_lines: ["SV", "OR"],
      point: [100, 300],
      geo_point: [-77.1, 38.9],
      position_type: "route",
    },
    {
      id: "2",
      line: null,
      point: null,
      geo_point: null,
      track_lines: [],
      position_type: "unknown",
    },
  ],
  updated_at: "2026-11-12T17:20:41Z",
};
function leafletFixture(window) {
  const markers = [];
  let map;
  const chain = () => ({
    on(name, action) {
      this[name] = action;
      return this;
    },
    addTo() {
      return this;
    },
    bindTooltip() {
      return this;
    },
    getElement() {
      return window.document.createElementNS(
        "http://www.w3.org/2000/svg",
        "path",
      );
    },
  });
  const leaflet = {
    map(container) {
      map = {
        center: [38.9, -77.1],
        zoom: 10,
        removed: false,
        getCenter() {
          return this.center;
        },
        getZoom() {
          return this.zoom;
        },
        getContainer() {
          return container;
        },
        getPane() {
          return container;
        },
        createPane() {
          return window.document.createElement("div");
        },
        fitBounds() {
          this.center = [38.9, -77.1];
          this.zoom = 10;
        },
        setView(center, zoom) {
          this.center = center;
          this.zoom = zoom;
        },
        invalidateSize() {},
        remove() {
          this.removed = true;
        },
      };
      return map;
    },
    tileLayer: chain,
    polyline: chain,
    circleMarker: chain,
    latLngBounds: (points) => points,
    layerGroup: () => ({ ...chain(), clearLayers() {} }),
    marker(point, options) {
      const marker = { ...chain(), point, options };
      markers.push(marker);
      return marker;
    },
    divIcon: (options) => options,
  };
  return {
    leaflet,
    markers,
    get map() {
      return map;
    },
  };
}
async function mapFixture(t, config = {}) {
  const window = new Window({ url: "http://localhost/" });
  window.eval(source);
  const mock = leafletFixture(window);
  window.L = mock.leaflet;
  const card = window.document.createElement("wmata-train-map");
  card._loadLeaflet = async () => mock.leaflet;
  card._routes = async () => ({
    paths: [
      {
        line: "SV",
        points: [
          [-77.1, 38.9],
          [-77.2, 39],
        ],
      },
    ],
    stations: [],
  });
  card.setConfig({ entity: "sensor.network", ...config });
  const hass = {
    themes: { darkMode: true },
    states: {
      "sensor.network": { state: "2", attributes: structuredClone(mapData) },
    },
    callWS: async () => ({ arrivals: [] }),
  };
  card.hass = hass;
  window.document.body.append(card);
  await new Promise((resolve) => setImmediate(resolve));
  t.after(async () => {
    card.remove();
    await window.happyDOM.close();
  });
  return { window, card, hass, mock };
}

test("map defaults to geographic, follows theme changes and preserves pan/zoom on refresh", async (t) => {
  const { card, hass, mock } = await mapFixture(t);
  assert.equal(card.view, "geographic");
  assert.equal(mock.markers.length, 1);
  assert.match(mock.map.getPane().style.filter, /invert/);
  mock.map.setView([39, -77.3], 13);
  card.hass = {
    ...hass,
    themes: { darkMode: false },
    states: {
      "sensor.network": { state: "2", attributes: structuredClone(mapData) },
    },
  };
  assert.deepEqual(mock.map.center, [39, -77.3]);
  assert.equal(mock.map.zoom, 13);
  assert.equal(mock.map.getPane().style.filter, "none");
  assert.equal(card.querySelector("details"), null);
  assert.match(card.textContent, /Last refreshed/);
  card.setConfig({ entity: "sensor.network", theme_mode: "dark" });
  await new Promise((resolve) => setImmediate(resolve));
  assert.match(mock.map.getPane().style.filter, /invert/);
});

test("train popups expand line names and closing a station popup stops its polling", async (t) => {
  const { card, hass, window } = await mapFixture(t);
  card._popup(mapData.trains[0]);
  assert.match(card.querySelector("dialog").textContent, /Line · Silver/);
  assert.match(
    card.querySelector("dialog").textContent,
    /Track serves · Silver, Orange/,
  );
  let calls = 0;
  card.hass = {
    ...hass,
    callWS: async (msg) => {
      calls++;
      assert.equal(msg.station_code, "C01");
      return {
        arrivals: [
          {
            line: "SV",
            destination: "Ashburn",
            direction: "Westbound",
            minutes: 4,
            status: "predicted",
          },
        ],
      };
    },
  };
  card._stationPopup({ code: "C01", name: "Metro Center" });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(calls, 1);
  assert.match(
    card.querySelector("dialog").textContent,
    /SilverAshburn · Westbound4 min/,
  );
  card.querySelector("dialog button").click();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(card._stationTimer, null);
  assert.equal(card.querySelector("dialog"), null);
  card._stationPopup({ code: "C01", name: "Metro Center" });
  card.remove();
  assert.equal(card._stationTimer, null);
});

test("switching views disposes the map and a delayed load cannot recreate a detached map", async (t) => {
  const { card, window, mock } = await mapFixture(t);
  const original = mock.map;
  const selector = card.querySelector('select[aria-label="Map view"]');
  selector.value = "diagram";
  selector.dispatchEvent(new window.Event("change"));
  assert.equal(card.view, "diagram");
  assert.equal(original.removed, true);
  assert.ok(card.querySelector("svg image"));
  assert.equal(card.querySelector("details"), null);
  const back = card.querySelector('select[aria-label="Map view"]');
  back.value = "geographic";
  back.dispatchEvent(new window.Event("change"));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(card.view, "geographic");
  assert.ok(card._map);
  let resolveRoutes;
  card.setConfig({ entity: "sensor.network" });
  card._routes = () =>
    new Promise((resolve) => {
      resolveRoutes = resolve;
    });
  // Start another mount while a route request is waiting.
  card._disposeGeo();
  card.last = null;
  card.hass = card._hass;
  await new Promise((resolve) => setImmediate(resolve));
  card.remove();
  resolveRoutes({ paths: [], stations: [] });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(card._map, null);
});

test("map YAML is validated and forced light overrides an HA dark theme", async (t) => {
  const { card, mock } = await mapFixture(t, { theme_mode: "light" });
  assert.equal(mock.map.getPane().style.filter, "none");
  assert.throws(() => card.setConfig({ view: "invalid" }), /view/);
  assert.throws(() => card.setConfig({ theme_mode: "invalid" }), /theme_mode/);
  assert.throws(() => card.setConfig({ dark_mode: "yes" }), /dark_mode/);
});

test("rail rows display travel directions without platform group numbers", (t) => {
  const { card } = fixture(t);
  const details = [...card.shadowRoot.querySelectorAll(".details")].map(
    (row) => row.textContent,
  );
  assert.match(details[0], /Westbound/);
  assert.match(details[1], /Direction unavailable/);
  assert.doesNotMatch(card.shadowRoot.textContent, /Platform group/);
});

test("appearance presets and journey instructions preserve the arrival data", (t) => {
  const { card, hass, root } = fixture(t, sample, { appearance: "native" });
  assert.equal(card.dataset.appearance, "native");
  for (const appearance of [
    "minimal",
    "mushroom",
    "glass",
    "daylight",
    "orbit",
    "bento",
  ]) {
    card.setConfig({ entity: "sensor.wmata_g01_arrivals", appearance });
    assert.equal(card.dataset.appearance, appearance);
    assert.equal(root.querySelectorAll(".arrival").length, 3);
  }
  assert.throws(
    () =>
      card.setConfig({
        entity: "sensor.wmata_g01_arrivals",
        appearance: "invalid",
      }),
    /appearance/,
  );
  const state = hass.states["sensor.wmata_g01_arrivals"];
  card.hass = {
    ...hass,
    states: {
      ...hass.states,
      "sensor.wmata_g01_arrivals": {
        ...state,
        attributes: {
          ...state.attributes,
          board_type: "journey",
          journey_route: { origin_name: "Union Station" },
          route_description:
            "Board Red to Gallery Place. Change to Yellow to Huntington.",
        },
      },
    },
  };
  assert.match(
    root.querySelector(".journey-route").textContent,
    /Change to Yellow/,
  );
  assert.match(
    root.querySelector(".journey-route").textContent,
    /Transfer waits and travel time are not included/,
  );
});

test("map frame appearance is separate from the basemap brightness", async (t) => {
  const { card } = await mapFixture(t, {
    appearance: "native",
    theme_mode: "dark",
  });
  assert.equal(card.querySelector("ha-card").dataset.appearance, "native");
  assert.equal(
    card.querySelector("ha-card").style.borderRadius,
    "var(--ha-card-border-radius, 12px)",
  );
});

const transferRoute = {
  origin_name: "Foggy Bottom-GWU",
  legs: [
    {
      from: "C04",
      to: "A01",
      from_name: "Foggy Bottom-GWU",
      to_name: "Metro Center",
    },
    {
      from: "A01",
      to: "B35",
      from_name: "Metro Center",
      to_name: "NoMa-Gallaudet U",
    },
  ],
};
const transferResponse = () => ({
  legs: [
    { index: 0, available: true, arrivals: [] },
    {
      index: 1,
      available: true,
      updated_at: new Date().toISOString(),
      arrivals: [
        {
          line: "RD",
          destination: "Glenmont",
          direction: "Eastbound",
          minutes: 2,
          status: "predicted",
        },
        {
          line: "RD",
          destination: "Silver Spring",
          direction: "Eastbound",
          minutes: 9,
          status: "predicted",
        },
      ],
    },
  ],
});
function setTransferJourney(f, callWS) {
  const original = f.hass.states["sensor.wmata_g01_arrivals"];
  f.card.hass = {
    ...f.hass,
    callWS,
    states: {
      ...f.hass.states,
      "sensor.wmata_g01_arrivals": {
        ...original,
        attributes: {
          ...original.attributes,
          board_type: "journey",
          journey_route: transferRoute,
          route_description:
            "Board Orange to Metro Center. Change to Red to NoMa-Gallaudet U.",
          arrivals: [
            {
              line: "OR",
              destination: "New Carrollton",
              minutes: 4,
              status: "predicted",
            },
          ],
        },
      },
    },
  };
}

test("journey card renders origin and live transfer rows with independent timestamps", async (t) => {
  const f = fixture(t);
  let calls = 0;
  setTransferJourney(f, async (msg) => {
    calls++;
    assert.equal(msg.type, "wmata/journey_arrivals");
    return transferResponse();
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(f.root.querySelectorAll(".rows .arrival").length, 1);
  assert.equal(
    f.root.querySelectorAll(".journey-transfers .arrival").length,
    2,
  );
  assert.match(
    f.root.querySelector(".transfer-title").textContent,
    /Metro Center → NoMa/,
  );
  assert.match(
    f.root.querySelector(".transfer-updated").textContent,
    /Updated/,
  );
  assert.match(
    f.root.querySelector(".transfer-note").textContent,
    /not guaranteed/,
  );
  f.card.setConfig({ entity: "sensor.wmata_g01_arrivals", transfer_rows: 1 });
  assert.equal(
    f.root.querySelectorAll(".journey-transfers .arrival").length,
    1,
  );
  assert.equal(calls, 1);
  assert.throws(
    () =>
      f.card.setConfig({
        entity: "sensor.wmata_g01_arrivals",
        transfer_rows: 0,
      }),
    /transfer_rows/,
  );
});

test("transfer failures leave the origin usable and do not expose error text", async (t) => {
  const f = fixture(t);
  setTransferJourney(f, async () => {
    throw new Error("private-response-detail");
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(f.root.querySelectorAll(".rows .arrival").length, 1);
  assert.match(
    f.root.querySelector(".transfer-status").textContent,
    /temporarily unavailable/,
  );
  assert.doesNotMatch(f.root.textContent, /private-response-detail/);
});

test("disabling or removing a journey card cancels transfer polling and ignores late responses", async (t) => {
  const f = fixture(t);
  let resolveRequest;
  setTransferJourney(
    f,
    () =>
      new Promise((resolve) => {
        resolveRequest = resolve;
      }),
  );
  assert.ok(f.card._transferTimer);
  f.card.setConfig({
    entity: "sensor.wmata_g01_arrivals",
    show_transfer_predictions: false,
  });
  assert.equal(f.card._transferTimer, null);
  assert.equal(f.root.querySelector(".journey-transfers"), null);
  resolveRequest(transferResponse());
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(f.card._transferData, null);
  f.card.setConfig({
    entity: "sensor.wmata_g01_arrivals",
    show_transfer_predictions: true,
  });
  assert.ok(f.card._transferTimer);
  f.card.remove();
  assert.equal(f.card._transferTimer, null);
  resolveRequest(transferResponse());
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(f.card._transferData, null);
});

test("stale transfer snapshots are labeled and hidden pages do not poll", async (t) => {
  const f = fixture(t);
  let calls = 0;
  setTransferJourney(f, async () => {
    calls++;
    const result = transferResponse();
    result.legs[1].updated_at = new Date(Date.now() - 180000).toISOString();
    return result;
  });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(f.root.querySelector(".transfer-updated").dataset.stale, "true");
  Object.defineProperty(f.window.document, "visibilityState", {
    configurable: true,
    value: "hidden",
  });
  await f.card._fetchTransfers();
  assert.equal(calls, 1);
});

test("the journey editor exposes transfer visibility and row count without duplicate fields", async (t) => {
  const f = fixture(t);
  setTransferJourney(f, async () => transferResponse());
  await new Promise((resolve) => setImmediate(resolve));
  const editor = f.window.document.createElement("wmata-station-card-editor");
  editor.setConfig({ entity: "sensor.wmata_g01_arrivals" });
  editor.hass = f.card._hass;
  editor.hass = f.card._hass;
  const form = editor.querySelector("ha-form");
  assert.equal(
    form.schema.filter((field) => field.name === "show_transfer_predictions")
      .length,
    1,
  );
  assert.equal(
    form.schema.filter((field) => field.name === "transfer_rows").length,
    1,
  );
  assert.equal(form.data.show_transfer_predictions, true);
  assert.equal(form.data.transfer_rows, 3);
});
