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
    /Train countdowns below show time until boarding/,
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
    { index: 0, available: true, arrivals: [], ride_minutes: 4 },
    {
      index: 1,
      ride_minutes: 8,
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
    show_destination_eta: false,
  });
  assert.equal(f.card._transferTimer, null);
  assert.equal(f.root.querySelector(".journey-transfers"), null);
  resolveRequest(transferResponse());
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(f.card._transferData, null);
  f.card.setConfig({
    entity: "sensor.wmata_g01_arrivals",
    show_transfer_predictions: true,
    show_destination_eta: true,
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
  assert.equal(form.data.transfer_buffer, 3);
  assert.equal(form.data.show_destination_eta, true);
  assert.equal(
    form.schema.filter((field) => field.name === "show_destination_eta").length,
    1,
  );
  assert.equal(
    form.schema.filter((field) => field.name === "transfer_buffer").length,
    1,
  );
});

async function estimatedJourney(t, times, config = {}, transform = () => {}) {
  const f = fixture(t, sample, config);
  const stamp = new Date().toISOString();
  const result = transferResponse();
  result.legs[1].updated_at = stamp;
  result.legs[1].arrivals = times.map((minutes) => ({
    ...result.legs[1].arrivals[0],
    minutes,
  }));
  transform(result);
  setTransferJourney(f, async () => result);
  f.card._hass.states["sensor.wmata_g01_arrivals"].attributes.updated_at =
    stamp;
  await new Promise((resolve) => setImmediate(resolve));
  return { ...f, result, stamp };
}

test("transfer estimates add ride and platform time and include the boundary departure", async (t) => {
  const f = await estimatedJourney(t, [2, 10, 11, 15], { transfer_rows: 4 });
  const rows = [...f.root.querySelectorAll(".transfer-arrivals .arrival")];
  assert.deepEqual(
    rows.map((row) => row.dataset.connection),
    ["early", "early", "likely", "likely"],
  );
  assert.match(rows[2].textContent, /Suggested connection/);
  assert.match(rows[3].textContent, /Also likely catchable/);
  const plan = f.card._connectionPlan();
  assert.equal(plan.legs[0].reach, Date.parse(f.stamp) + 8 * 60000);
  assert.equal(plan.legs[0].ready, Date.parse(f.stamp) + 11 * 60000);
  assert.match(
    f.root.querySelector(".transfer-station .connection-summary").textContent,
    /3 min to change/,
  );
});

test("row limits keep the suggested connection visible and the buffer is editable", async (t) => {
  const f = await estimatedJourney(t, [1, 3, 5, 11, 15], { transfer_rows: 2 });
  let rows = [...f.root.querySelectorAll(".transfer-arrivals .arrival")];
  assert.equal(rows.length, 2);
  assert.equal(rows[1].querySelector(".eta").textContent, "11min");
  assert.match(rows[1].textContent, /Suggested connection/);
  f.card.setConfig({
    entity: "sensor.wmata_g01_arrivals",
    transfer_buffer: 6,
    transfer_rows: 2,
  });
  rows = [...f.root.querySelectorAll(".transfer-arrivals .arrival")];
  assert.equal(rows[1].querySelector(".eta").textContent, "15min");
  assert.match(rows[1].textContent, /Suggested connection/);
  for (const transfer_buffer of [0, -1, 1.5, "3", 31])
    assert.throws(
      () =>
        f.card.setConfig({
          entity: "sensor.wmata_g01_arrivals",
          transfer_buffer,
        }),
      /transfer_buffer/,
    );
});

test("old snapshots and unknown or delayed estimates cannot become likely connections", async (t) => {
  const f = await estimatedJourney(t, [12, null], {}, (result) => {
    result.legs[1].arrivals[1].status = "delayed";
  });
  assert.deepEqual(
    [...f.root.querySelectorAll(".transfer-arrivals .arrival")].map(
      (row) => row.dataset.connection,
    ),
    ["likely", "unknown"],
  );
  f.result.legs[1].updated_at = new Date(Date.now() - 180000).toISOString();
  f.card._updateFreshness();
  assert.equal(f.root.querySelectorAll('[data-connection="likely"]').length, 0);
  f.result.legs[1].updated_at = f.stamp;
  f.card._hass.states["sensor.wmata_g01_arrivals"].attributes.updated_at =
    new Date(Date.now() - 180000).toISOString();
  f.card._updateFreshness();
  assert.equal(f.root.querySelectorAll('[data-connection="likely"]').length, 0);
  assert.match(f.root.textContent, /No fresh origin departure/);
});

test("missing ride times leave departures readable and later windows are not invented", async (t) => {
  const f = await estimatedJourney(t, [2, 5]);
  assert.match(
    f.root.textContent,
    /No catchable trains in the current prediction window/,
  );
  f.result.legs[0].ride_minutes = null;
  f.card._renderTransfers();
  assert.match(f.root.textContent, /Scheduled ride time is unavailable/);
  assert.equal(f.root.querySelectorAll('[data-connection="likely"]').length, 0);
  assert.equal(
    f.root.querySelectorAll(".transfer-arrivals .arrival").length,
    2,
  );
});

test("multiple transfers propagate the chosen departure plus the next ride and buffer", async (t) => {
  const f = await estimatedJourney(t, [2, 12]);
  f.card._hass.states["sensor.wmata_g01_arrivals"].attributes.journey_route = {
    ...transferRoute,
    legs: [
      ...transferRoute.legs,
      {
        from: "B35",
        to: "B11",
        from_name: "NoMa-Gallaudet U",
        to_name: "Glenmont",
      },
    ],
  };
  f.result.legs[1].ride_minutes = 6;
  f.result.legs.push({
    index: 2,
    available: true,
    updated_at: f.stamp,
    arrivals: [
      { ...f.result.legs[1].arrivals[0], minutes: 20 },
      { ...f.result.legs[1].arrivals[0], minutes: 22 },
    ],
  });
  f.card._renderTransfers();
  const plan = f.card._connectionPlan();
  assert.equal(plan.legs[1].ready, Date.parse(f.stamp) + 21 * 60000);
  assert.equal(plan.legs[1].chosen.minutes, 22);
  f.result.legs[1].arrivals = f.result.legs[1].arrivals.slice(0, 1);
  f.card._renderTransfers();
  assert.equal(f.card._connectionPlan().legs[1].ready, undefined);
  assert.match(
    f.root.textContent,
    /No catchable train is predicted for the preceding leg/,
  );
});

test("connection estimates account for different snapshot ages and origin filters", async (t) => {
  const f = await estimatedJourney(t, [11, 12]);
  f.result.legs[1].updated_at = new Date(
    Date.parse(f.stamp) - 60000,
  ).toISOString();
  f.card._renderTransfers();
  assert.equal(f.card._connectionPlan().legs[0].chosen.minutes, 12);
  f.card.setConfig({ entity: "sensor.wmata_g01_arrivals", lines: ["SV"] });
  assert.equal(f.card._connectionPlan().origin, undefined);
  assert.equal(f.root.querySelectorAll('[data-connection="likely"]').length, 0);
});

test("destination arrival includes origin wait, rides, platform changes and connection waits once", async (t) => {
  const f = await estimatedJourney(t, [2, 12, 15]);
  const plan = f.card._connectionPlan();
  // 4 min origin wait + 4 min ride + 3 min changing + 1 min wait + 8 min final ride.
  assert.equal(plan.arrival, Date.parse(f.stamp) + 20 * 60000);
  assert.match(
    f.root.querySelector(".journey-eta").textContent,
    /Estimated arrival · NoMa-Gallaudet U/,
  );
  assert.match(
    f.root.querySelector(".journey-eta-details").textContent,
    /About 20 min from now/,
  );
  assert.match(
    f.root.querySelector(".journey-eta").textContent,
    /transfer waits, and 3 min to switch platforms/,
  );
  assert.equal(
    f.root.querySelector(".journey-route").nextElementSibling.className,
    "journey-eta",
  );
  f.card.setConfig({ entity: "sensor.wmata_g01_arrivals", transfer_buffer: 6 });
  assert.equal(
    f.card._connectionPlan().arrival,
    Date.parse(f.stamp) + 23 * 60000,
  );
  assert.match(
    f.root.querySelector(".journey-eta").textContent,
    /6 min to switch/,
  );
});

test("destination arrival stops when any connection, final ride or fresh prediction is missing", async (t) => {
  const f = await estimatedJourney(t, [2, 5]);
  assert.equal(f.card._connectionPlan().arrival, undefined);
  assert.match(
    f.root.querySelector(".journey-eta").textContent,
    /No catchable connection/,
  );
  assert.equal(f.root.querySelector(".journey-eta-time"), null);
  f.result.legs[1].arrivals[1].minutes = 12;
  f.result.legs[1].ride_minutes = null;
  f.card._renderTransfers();
  assert.match(
    f.root.querySelector(".journey-eta").textContent,
    /Scheduled ride time is unavailable/,
  );
  f.result.legs[1].ride_minutes = 8;
  f.card._renderTransfers();
  assert.ok(f.root.querySelector(".journey-eta-time"));
  f.result.legs[1].updated_at = new Date(Date.now() - 180000).toISOString();
  f.card._updateFreshness();
  assert.equal(f.root.querySelector(".journey-eta-time"), null);
  assert.match(
    f.root.querySelector(".journey-eta").textContent,
    /Waiting for fresh transfer predictions/,
  );
  f.result.legs[1].updated_at = f.stamp;
  f.card._transferError = true;
  f.card._renderTransfers();
  assert.match(
    f.root.querySelector(".journey-eta").textContent,
    /temporarily unavailable/,
  );
});

test("multiple-transfer destination arrival uses the last suggested train and its ride", async (t) => {
  const f = await estimatedJourney(t, [12]);
  f.card._hass.states["sensor.wmata_g01_arrivals"].attributes.journey_route = {
    ...transferRoute,
    destination_name: "Glenmont",
    legs: [
      ...transferRoute.legs,
      {
        from: "B35",
        to: "B11",
        from_name: "NoMa-Gallaudet U",
        to_name: "Glenmont",
      },
    ],
  };
  f.result.legs[1].ride_minutes = 6;
  f.result.legs.push({
    index: 2,
    available: true,
    updated_at: f.stamp,
    ride_minutes: 20,
    arrivals: [{ ...f.result.legs[1].arrivals[0], minutes: 22 }],
  });
  f.card._renderTransfers();
  assert.equal(
    f.card._connectionPlan().arrival,
    Date.parse(f.stamp) + 42 * 60000,
  );
  assert.match(f.root.querySelector(".journey-eta").textContent, /Glenmont/);
});

test("destination summary works without displaying transfer boards and can be hidden independently", async (t) => {
  const f = await estimatedJourney(t, [12], {
    show_transfer_predictions: false,
  });
  assert.equal(f.root.querySelector(".journey-transfers"), null);
  assert.ok(f.root.querySelector(".journey-eta-time"));
  assert.ok(f.card._transferTimer);
  f.card.setConfig({
    entity: "sensor.wmata_g01_arrivals",
    show_destination_eta: false,
  });
  assert.equal(f.root.querySelector(".journey-eta"), null);
  assert.ok(f.root.querySelector(".journey-transfers"));
  assert.ok(f.card._transferTimer);
  f.card.setConfig({
    entity: "sensor.wmata_g01_arrivals",
    show_destination_eta: false,
    show_transfer_predictions: false,
  });
  assert.equal(f.card._transferTimer, null);
  assert.throws(
    () =>
      f.card.setConfig({
        entity: "sensor.wmata_g01_arrivals",
        show_destination_eta: "yes",
      }),
    /show_destination_eta/,
  );
});

test("direct journeys fetch ride times for the destination ETA without transfer boards", async (t) => {
  const f = fixture(t);
  let calls = 0;
  const stamp = new Date().toISOString();
  const original = f.hass.states["sensor.wmata_g01_arrivals"];
  f.card.hass = {
    ...f.hass,
    states: {
      "sensor.wmata_g01_arrivals": {
        ...original,
        attributes: {
          ...original.attributes,
          board_type: "journey",
          updated_at: stamp,
          journey_route: {
            origin_name: "Foggy Bottom-GWU",
            destination_name: "Metro Center",
            legs: [transferRoute.legs[0]],
          },
          arrivals: [{ ...sample[0], minutes: 4 }],
        },
      },
    },
    callWS: async () => {
      calls++;
      return {
        legs: [
          {
            index: 0,
            available: true,
            updated_at: stamp,
            ride_minutes: 4,
            arrivals: [],
          },
        ],
      };
    },
  };
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(calls, 1);
  assert.equal(f.root.querySelector(".journey-transfers"), null);
  assert.equal(f.card._connectionPlan().arrival, Date.parse(stamp) + 8 * 60000);
  assert.match(
    f.root.querySelector(".journey-eta").textContent,
    /Metro Center/,
  );
  assert.doesNotMatch(
    f.root.querySelector(".journey-eta").textContent,
    /platforms|transfer waits/,
  );
  const editor = f.window.document.createElement("wmata-station-card-editor");
  editor.setConfig({ entity: "sensor.wmata_g01_arrivals" });
  editor.hass = f.card._hass;
  const names = editor
    .querySelector("ha-form")
    .schema.map((field) => field.name);
  assert.ok(names.includes("show_destination_eta"));
  assert.ok(!names.includes("transfer_buffer"));
  f.card.setConfig({
    entity: "sensor.wmata_g01_arrivals",
    show_destination_eta: false,
  });
  assert.equal(f.card._transferTimer, null);
});

test("choosing a later origin train recalculates transfers and the final ETA without querying again", async (t) => {
  const f = await estimatedJourney(t, [12, 16, 20]);
  const state = f.card._hass.states["sensor.wmata_g01_arrivals"];
  state.attributes.arrivals.push({
    ...state.attributes.arrivals[0],
    line: "SV",
    destination: "Downtown Largo",
    minutes: 7,
  });
  f.card._render();
  assert.equal(f.card._connectionPlan().legs[0].chosen.minutes, 12);
  const data = f.card._transferData;
  f.root.querySelectorAll(".origin-choice")[1].click();
  assert.equal(f.card._connectionPlan().origin.line, "SV");
  assert.equal(f.card._connectionPlan().legs[0].chosen.minutes, 16);
  assert.equal(
    f.card._connectionPlan().arrival,
    Date.parse(f.stamp) + 24 * 60000,
  );
  assert.strictEqual(f.card._transferData, data);
  assert.equal(
    f.root.querySelectorAll(".origin-choice")[1].getAttribute("aria-pressed"),
    "true",
  );
  assert.match(
    f.root.querySelector(".journey-eta").textContent,
    /selected origin train/,
  );
  f.root.querySelector(".origin-reset").click();
  assert.equal(f.card._connectionPlan().origin.line, "OR");
  assert.equal(f.card._connectionPlan().legs[0].chosen.minutes, 12);
});

test("a selected origin follows its countdown and disappearing predictions require reselection", async (t) => {
  const f = await estimatedJourney(t, [12, 16]);
  const state = f.card._hass.states["sensor.wmata_g01_arrivals"];
  state.attributes.arrivals.push({
    ...state.attributes.arrivals[0],
    minutes: 7,
  });
  f.card._render();
  f.root.querySelectorAll(".origin-choice")[1].click();
  const next = {
    ...state,
    attributes: {
      ...state.attributes,
      arrivals: [
        { ...state.attributes.arrivals[0], minutes: 3 },
        { ...state.attributes.arrivals[1], minutes: 6 },
      ],
      updated_at: new Date(Date.parse(f.stamp) + 10000).toISOString(),
    },
  };
  f.card.hass = {
    ...f.card._hass,
    states: { ...f.card._hass.states, "sensor.wmata_g01_arrivals": next },
  };
  assert.equal(f.card._connectionPlan().origin.minutes, 6);
  next.attributes.arrivals = [{ ...next.attributes.arrivals[0], minutes: 3 }];
  f.card._render();
  assert.equal(f.card._connectionPlan().origin, undefined);
  assert.match(
    f.root.querySelector(".journey-eta").textContent,
    /selected train is no longer predicted/,
  );
  assert.equal(f.root.querySelectorAll('[data-connection="likely"]').length, 0);
  f.root.querySelector(".origin-reset").click();
  assert.equal(f.card._connectionPlan().origin.minutes, 3);
});

function quickTripResponse() {
  const stamp = new Date().toISOString();
  return {
    route: {
      ...transferRoute,
      origin: "C04",
      destination: "B35",
      destination_name: "NoMa-Gallaudet U",
    },
    route_description:
      "Board Orange / Silver to Metro Center. Change to Red to NoMa-Gallaudet U.",
    scheduled_ride_minutes: 12,
    legs: [
      {
        index: 0,
        available: true,
        ride_minutes: 4,
        updated_at: stamp,
        arrivals: [
          {
            line: "OR",
            destination: "New Carrollton",
            minutes: 4,
            status: "predicted",
          },
          {
            line: "SV",
            destination: "Downtown Largo",
            minutes: 7,
            status: "predicted",
          },
        ],
      },
      {
        index: 1,
        available: true,
        ride_minutes: 8,
        updated_at: stamp,
        arrivals: [12, 16, 20].map((minutes) => ({
          line: "RD",
          destination: "Glenmont",
          minutes,
          status: "predicted",
        })),
      },
    ],
  };
}
async function plannerFixture(t, handler, config = {}, stationList) {
  const f = fixture(t);
  const requests = [];
  const planner = f.window.document.createElement("wmata-trip-planner");
  planner.setConfig({ entity: "sensor.wmata_g01_arrivals", ...config });
  planner.hass = {
    ...f.hass,
    callWS: async (msg) => {
      requests.push(msg);
      if (msg.type === "wmata/planner_stations")
        return {
          stations: stationList || [
            {
              code: "C04",
              name: "Foggy Bottom-GWU",
              lines: ["OR", "SV", "BL"],
            },
            {
              code: "A01",
              name: "Metro Center",
              lines: ["RD", "OR", "SV", "BL"],
            },
            { code: "B35", name: "NoMa-Gallaudet U", lines: ["RD"] },
          ],
        };
      return handler ? handler(msg) : quickTripResponse();
    },
  };
  f.window.document.body.append(planner);
  await new Promise((resolve) => setImmediate(resolve));
  const root = planner.shadowRoot;
  return { ...f, planner, plannerRoot: root, requests };
}
async function planQuickTrip(f, from = "Foggy", to = "NoMa") {
  f.planner._originInput.value = from;
  f.planner._destinationInput.value = to;
  f.plannerRoot
    .querySelector("form")
    .dispatchEvent(new f.window.Event("submit", { cancelable: true }));
  await new Promise((resolve) => setImmediate(resolve));
}

test("quick planner resolves station names, shows scheduled and live estimates and allows later trains", async (t) => {
  const f = await plannerFixture(t);
  assert.equal(f.plannerRoot.querySelectorAll("datalist option").length, 3);
  await planQuickTrip(f);
  assert.deepEqual(
    f.requests.map((r) => r.type),
    ["wmata/planner_stations", "wmata/plan_trip"],
  );
  assert.equal(f.requests[1].origin, "C04");
  assert.equal(f.requests[1].destination, "B35");
  assert.match(
    f.plannerRoot.querySelector(".scheduled").textContent,
    /15 min riding and switching platforms, plus train waits/,
  );
  const board = f.plannerRoot.querySelector("wmata-station-card");
  assert.ok(board.shadowRoot.querySelector(".journey-eta-time"));
  board.shadowRoot.querySelectorAll(".origin-choice")[1].click();
  assert.equal(board._connectionPlan().origin.line, "SV");
  assert.equal(board._connectionPlan().legs[0].chosen.minutes, 16);
  assert.equal(f.requests.length, 2);
  assert.equal(board._transferTimer, null);
  assert.ok(f.window.customCards.some((c) => c.type === "wmata-trip-planner"));
});

test("quick planner swaps stations and partial edits clear old routes without sending requests", async (t) => {
  const f = await plannerFixture(t);
  await planQuickTrip(f);
  f.planner._originInput.value = "Metro";
  f.planner._originInput.dispatchEvent(new f.window.Event("input"));
  assert.equal(f.plannerRoot.querySelector("wmata-station-card"), null);
  assert.equal(f.requests.length, 2);
  f.planner._originInput.value = "Foggy Bottom-GWU";
  f.planner._destinationInput.value = "NoMa-Gallaudet U";
  [...f.plannerRoot.querySelectorAll("button")]
    .find((b) => b.textContent === "Swap stations")
    .click();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(f.requests.at(-1).origin, "B35");
  assert.equal(f.requests.at(-1).destination, "C04");
});

test("quick planner keeps a scheduled estimate when live connections are outside the prediction window", async (t) => {
  const f = await plannerFixture(t, () => {
    const result = quickTripResponse();
    result.legs[1].arrivals = result.legs[1].arrivals.slice(0, 1);
    result.legs[1].arrivals[0].minutes = 2;
    return result;
  });
  await planQuickTrip(f);
  assert.match(f.plannerRoot.querySelector(".scheduled").textContent, /15 min/);
  const board = f.planner._board;
  assert.equal(board.shadowRoot.querySelector(".journey-eta-time"), null);
  assert.match(
    board.shadowRoot.querySelector(".journey-eta").textContent,
    /No catchable connection/,
  );
});

test("quick planner ignores late responses, avoids overlapping refreshes and pauses on hidden pages or removal", async (t) => {
  let resolve;
  const f = await plannerFixture(
    t,
    () =>
      new Promise((r) => {
        resolve = r;
      }),
  );
  await planQuickTrip(f);
  await f.planner._refresh();
  assert.equal(f.requests.length, 2);
  f.planner._destinationInput.dispatchEvent(new f.window.Event("input"));
  resolve(quickTripResponse());
  await new Promise((r) => setImmediate(r));
  assert.equal(f.plannerRoot.querySelector("wmata-station-card"), null);
  Object.defineProperty(f.window.document, "visibilityState", {
    configurable: true,
    value: "hidden",
  });
  await planQuickTrip(f);
  assert.equal(f.requests.length, 2);
  Object.defineProperty(f.window.document, "visibilityState", {
    configurable: true,
    value: "visible",
  });
  await planQuickTrip(f);
  assert.equal(f.requests.length, 3);
  f.planner.remove();
  resolve(quickTripResponse());
  await new Promise((r) => setImmediate(r));
  assert.equal(f.planner._timer, null);
  assert.equal(f.plannerRoot.querySelector("wmata-station-card"), null);
});

test("quick planner validates inputs and failures do not expose API details or revive stale highlights", async (t) => {
  let fail = false;
  const f = await plannerFixture(t, () => {
    if (fail) throw new Error("private response");
    return quickTripResponse();
  });
  await planQuickTrip(f, "unknown", "NoMa");
  assert.equal(f.requests.length, 1);
  assert.match(
    f.plannerRoot.querySelector(".status").textContent,
    /Choose two different stations/,
  );
  await planQuickTrip(f);
  fail = true;
  await f.planner._refresh();
  assert.match(
    f.plannerRoot.querySelector(".status").textContent,
    /unavailable/,
  );
  assert.doesNotMatch(f.plannerRoot.textContent, /private response/);
  f.planner.hass = { ...f.planner._hass };
  assert.equal(
    f.planner._board.shadowRoot.querySelector(".journey-eta-time"),
    null,
  );
  assert.equal(
    f.planner._board.shadowRoot.querySelectorAll('[data-connection="likely"]')
      .length,
    0,
  );
});

test("planner refresh preserves the chosen origin train and the editor uses an existing rail entity", async (t) => {
  const f = await plannerFixture(t);
  await planQuickTrip(f);
  f.planner._board.shadowRoot.querySelectorAll(".origin-choice")[1].click();
  await f.planner._refresh();
  assert.equal(f.planner._board._connectionPlan().origin.line, "SV");
  assert.ok(f.planner._board._originSelection);
  const editor = f.window.document.createElement("wmata-trip-planner-editor");
  editor.setConfig({ entity: "sensor.wmata_g01_arrivals" });
  editor.hass = f.planner._hass;
  const form = editor.querySelector("ha-form");
  assert.equal(form.data.transfer_buffer, 3);
  assert.equal(form.data.appearance, "native");
  assert.equal(
    form.schema.filter((field) => field.name === "entity").length,
    1,
  );
  let changed;
  editor.addEventListener("config-changed", (event) => {
    changed = event.detail.config;
  });
  form.dispatchEvent(
    new f.window.CustomEvent("value-changed", {
      detail: { value: { transfer_buffer: 5 } },
    }),
  );
  assert.equal(changed.transfer_buffer, 5);
  assert.equal(changed.entity, "sensor.wmata_g01_arrivals");
  assert.throws(
    () => f.planner.setConfig({ entity: "sensor.rail", transfer_buffer: 0 }),
    /transfer_buffer/,
  );
});

function scheduleDeparture(stamp, departure, arrival, line = "RD") {
  return {
    line,
    line_name: line === "RD" ? "Red" : "Orange",
    destination: line === "RD" ? "Glenmont" : "New Carrollton",
    destination_code: line === "RD" ? "B11" : "D13",
    status: "predicted",
    prediction_source: "schedule",
    departure_at: new Date(Date.parse(stamp) + departure * 60000).toISOString(),
    station_arrival_at: new Date(
      Date.parse(stamp) + departure * 60000,
    ).toISOString(),
    arrival_at: new Date(Date.parse(stamp) + arrival * 60000).toISOString(),
  };
}
test("future transfers use labeled timetable estimates with exact trip arrival times and totals", async (t) => {
  const f = await estimatedJourney(t, [2, 5]);
  f.result.legs[1].scheduled_departures = [scheduleDeparture(f.stamp, 18, 29)];
  f.card._render();
  const plan = f.card._connectionPlan();
  assert.equal(plan.arrival, Date.parse(f.stamp) + 29 * 60000);
  assert.equal(plan.schedule_estimate, true);
  assert.equal(plan.trip_minutes, 25);
  assert.equal(plan.ride_minutes, 15);
  assert.equal(plan.platform_minutes, 3);
  assert.equal(plan.transfer_wait_minutes, 7);
  assert.match(
    f.root.querySelector(".journey-eta-heading").textContent,
    /Schedule-based arrival/,
  );
  assert.match(
    f.root.querySelector(".trip-total").textContent,
    /25 min.*15 min riding.*3 min switching.*7 min waiting/,
  );
  assert.equal(f.root.querySelectorAll(".trip-itinerary li").length, 2);
  assert.match(
    f.root.querySelector(".trip-itinerary").textContent,
    /Timetable estimate, not live/,
  );
  assert.match(
    f.root.querySelector('[data-source="schedule"]').textContent,
    /Schedule estimate.*possible connection/,
  );
});
test("scheduled departures never replace live predictions within the reported window", async (t) => {
  const f = await estimatedJourney(t, [12, 16, 20]);
  f.result.legs[1].scheduled_departures = [
    scheduleDeparture(f.stamp, 14, 22),
    scheduleDeparture(f.stamp, 19, 27),
    scheduleDeparture(f.stamp, 22, 30),
  ];
  f.card._render();
  const arrivals = f.card._legArrivals(f.result.legs[1]);
  assert.equal(
    arrivals.filter((a) => a.prediction_source === "schedule").length,
    1,
  );
  assert.equal(f.card._connectionPlan().legs[0].chosen.minutes, 12);
  assert.equal(f.card._connectionPlan().schedule_estimate, false);
  assert.match(
    f.root.querySelector(".departure-clock").textContent,
    /Live.*expected/,
  );
});
test("a fully scheduled trip remains available when live data is stale and can select a later departure", async (t) => {
  const f = await estimatedJourney(t, []);
  const state = f.card._hass.states["sensor.wmata_g01_arrivals"];
  state.attributes.arrivals = [];
  state.attributes.updated_at = new Date(
    Date.parse(f.stamp) - 180000,
  ).toISOString();
  f.result.legs[0].scheduled_departures = [
    scheduleDeparture(f.stamp, 30, 34, "OR"),
    scheduleDeparture(f.stamp, 40, 44, "OR"),
  ];
  f.result.legs[1].available = false;
  f.result.legs[1].scheduled_departures = [
    scheduleDeparture(f.stamp, 40, 49),
    scheduleDeparture(f.stamp, 50, 59),
  ];
  f.card._render();
  assert.equal(
    f.card._connectionPlan().arrival,
    Date.parse(f.stamp) + 49 * 60000,
  );
  f.root.querySelectorAll(".origin-choice")[1].click();
  assert.equal(
    f.card._connectionPlan().arrival,
    Date.parse(f.stamp) + 59 * 60000,
  );
  assert.equal(f.card._connectionPlan().origin.prediction_source, "schedule");
  assert.match(
    f.root.querySelector(".journey-eta").textContent,
    /Schedule-based arrival/,
  );
});
test("planner and result share the dashboard appearance and Daylight day-night state", async (t) => {
  const f = await plannerFixture(t, undefined, { appearance: "daylight" });
  f.planner.hass = {
    ...f.planner._hass,
    themes: { darkMode: true },
    states: {
      ...f.planner._hass.states,
      "sun.sun": { state: "above_horizon" },
    },
  };
  await planQuickTrip(f);
  assert.equal(f.planner.dataset.appearance, "daylight");
  assert.equal(f.planner.dataset.day, "true");
  assert.equal(f.planner._board.dataset.appearance, "daylight");
  assert.equal(f.planner._board.dataset.day, "true");
  assert.match(
    f.planner._board.shadowRoot.querySelector(".eyebrow").textContent,
    /TRIP PLAN/,
  );
  f.planner.hass = {
    ...f.planner._hass,
    states: {
      ...f.planner._hass.states,
      "sun.sun": { state: "below_horizon" },
    },
  };
  assert.equal(f.planner.dataset.day, "false");
  assert.equal(f.planner._board.dataset.day, "false");
  for (const appearance of ["orbit", "bento"]) {
    f.planner.setConfig({ entity: "sensor.wmata_g01_arrivals", appearance });
    await planQuickTrip(f);
    assert.equal(f.planner.dataset.appearance, appearance);
    assert.equal(f.planner._board.dataset.appearance, appearance);
  }
});

function competingTrips() {
  const stamp = new Date().toISOString();
  const direct = {
    id: "direct-blue",
    route: {
      origin: "C04",
      origin_name: "Foggy Bottom-GWU",
      destination: "C13",
      destination_name: "King St-Old Town",
      stops: 9,
      transfers: 0,
      legs: [
        {
          from: "C04",
          to: "C13",
          from_name: "Foggy Bottom-GWU",
          to_name: "King St-Old Town",
          lines: ["BL"],
        },
      ],
    },
    route_description: "Board Blue to King St-Old Town.",
    scheduled_ride_minutes: 22,
    legs: [
      {
        index: 0,
        available: true,
        updated_at: stamp,
        ride_minutes: 22,
        arrivals: [18, 25].map((minutes) => ({
          line: "BL",
          destination: "Franconia-Springfield",
          destination_code: "J03",
          minutes,
          status: "predicted",
        })),
      },
    ],
  };
  const change = {
    id: "via-lenfant",
    route: {
      origin: "C04",
      origin_name: "Foggy Bottom-GWU",
      destination: "C13",
      destination_name: "King St-Old Town",
      stops: 10,
      transfers: 1,
      legs: [
        {
          from: "C04",
          to: "D03",
          from_name: "Foggy Bottom-GWU",
          to_name: "L'Enfant Plaza",
          lines: ["OR", "SV"],
        },
        {
          from: "D03",
          to: "C13",
          from_name: "L'Enfant Plaza",
          to_name: "King St-Old Town",
          lines: ["YL"],
        },
      ],
    },
    route_description:
      "Board Orange / Silver to L'Enfant Plaza. Change to Yellow to King St-Old Town.",
    scheduled_ride_minutes: 20,
    legs: [
      {
        index: 0,
        available: true,
        updated_at: stamp,
        ride_minutes: 8,
        arrivals: [
          {
            line: "OR",
            destination: "New Carrollton",
            destination_code: "D13",
            minutes: 2,
            status: "predicted",
          },
        ],
      },
      {
        index: 1,
        available: true,
        updated_at: stamp,
        ride_minutes: 12,
        arrivals: [15, 30].map((minutes) => ({
          line: "YL",
          destination: "Huntington",
          destination_code: "C15",
          minutes,
          status: "predicted",
        })),
      },
    ],
  };
  return { ...direct, alternatives: [direct, change] };
}
async function comparisonFixture(t, handler, config = {}) {
  const f = await plannerFixture(
    t,
    handler || (() => competingTrips()),
    config,
    [
      { code: "C04", name: "Foggy Bottom-GWU", lines: ["BL", "OR", "SV"] },
      { code: "C13", name: "King St-Old Town", lines: ["BL", "YL"] },
    ],
  );
  await planQuickTrip(f, "Foggy", "King St");
  return f;
}
test("planner ranks arrival time ahead of transfer count and shows the time saved", async (t) => {
  const f = await comparisonFixture(t);
  assert.equal(f.planner._activeRouteId, "via-lenfant");
  assert.equal(f.planner._board._transferRoute().legs.length, 2);
  const buttons = f.plannerRoot.querySelectorAll(".route-choice");
  assert.match(buttons[0].textContent, /Fastest estimate.*L'Enfant/);
  assert.match(buttons[1].textContent, /Direct.*13 min later/);
  assert.equal(buttons[0].getAttribute("aria-pressed"), "true");
  assert.equal(
    f.requests.filter((r) => r.type === "wmata/plan_trip").length,
    1,
  );
});
test("platform-change allowance can change which route is fastest", async (t) => {
  const f = await comparisonFixture(t);
  assert.equal(f.planner._activeRouteId, "via-lenfant");
  f.planner.setConfig({
    entity: "sensor.wmata_g01_arrivals",
    transfer_buffer: 10,
  });
  await planQuickTrip(f, "Foggy", "King St");
  assert.equal(f.planner._activeRouteId, "direct-blue");
  assert.match(
    f.plannerRoot.querySelector(".route-choice").textContent,
    /Fastest estimate.*Direct/,
  );
});
test("an alternative can be inspected and a manually selected departure stays pinned until reset", async (t) => {
  const f = await comparisonFixture(t);
  [...f.plannerRoot.querySelectorAll(".route-choice")]
    .find((b) => b.textContent.includes("Direct"))
    .click();
  assert.equal(f.planner._activeRouteId, "direct-blue");
  f.planner._board.shadowRoot.querySelectorAll(".origin-choice")[1].click();
  assert.equal(f.planner._board._connectionPlan().origin.minutes, 25);
  await f.planner._refresh();
  assert.equal(f.planner._activeRouteId, "direct-blue");
  assert.equal(f.planner._board._connectionPlan().origin.minutes, 25);
  assert.match(
    f.plannerRoot.querySelector(".comparison-note").textContent,
    /selected departure/,
  );
  const count = f.requests.length;
  f.plannerRoot.querySelector(".fastest-reset").click();
  assert.equal(f.planner._activeRouteId, "via-lenfant");
  assert.equal(f.requests.length, count);
});
test("incomplete routes sort last and no fastest claim appears when all arrivals are unknown", async (t) => {
  let empty = false;
  const f = await comparisonFixture(t, () => {
    const result = competingTrips();
    result.alternatives[0].legs[0].arrivals = [];
    if (empty) result.alternatives[1].legs[0].arrivals = [];
    return result;
  });
  assert.equal(f.planner._activeRouteId, "via-lenfant");
  assert.match(
    f.plannerRoot.querySelectorAll(".route-choice")[1].textContent,
    /Arrival estimate unavailable/,
  );
  empty = true;
  await f.planner._refresh();
  assert.match(
    f.plannerRoot.querySelector(".comparison-summary").textContent,
    /No complete arrival estimates/,
  );
  assert.ok(
    [...f.plannerRoot.querySelectorAll(".route-choice")].every(
      (b) => !b.textContent.includes("Fastest estimate"),
    ),
  );
});
test("automatic ranking uses the earliest-arriving origin train rather than blindly taking the first departure", async (t) => {
  const f = await comparisonFixture(t, () => {
    const result = competingTrips();
    const direct = result.alternatives[0];
    const stamp = direct.legs[0].updated_at;
    direct.legs[0].arrivals = [];
    direct.legs[0].scheduled_departures = [
      scheduleDeparture(stamp, 5, 20, "BL"),
      scheduleDeparture(stamp, 8, 18, "BL"),
    ];
    return result;
  });
  assert.equal(f.planner._activeRouteId, "direct-blue");
  const plan = f.planner._board._connectionPlan();
  assert.equal(plan.origin.minutes, 8);
  assert.ok(f.planner._board._recommendedOrigin);
  assert.match(
    f.plannerRoot.querySelector(".route-choice").textContent,
    /Includes timetable estimates/,
  );
  assert.match(
    f.planner._board.shadowRoot.querySelector(".journey-eta").textContent,
    /recommended origin train/,
  );
});
test("route ranking chooses a later transfer departure when its timetable reaches the goal earlier", async (t) => {
  const f = await comparisonFixture(t, () => {
    const result = competingTrips();
    const leg = result.alternatives[1].legs[1];
    leg.arrivals = [];
    leg.scheduled_departures = [
      scheduleDeparture(leg.updated_at, 15, 40, "YL"),
      scheduleDeparture(leg.updated_at, 18, 30, "YL"),
    ];
    return result;
  });
  assert.equal(f.planner._activeRouteId, "via-lenfant");
  const plan = f.planner._board._connectionPlan();
  assert.equal(plan.legs[0].chosen.minutes, 18);
  assert.equal(plan.schedule_estimate, true);
});

test("a recommended origin remains visible when it falls beyond the normal row limit", async (t) => {
  const f = await comparisonFixture(t, () => {
    const result = competingTrips();
    const leg = result.alternatives[0].legs[0];
    leg.arrivals = [];
    leg.scheduled_departures = [
      ...Array.from({ length: 9 }, (_, i) =>
        scheduleDeparture(leg.updated_at, 5 + i, 35 + i, "BL"),
      ),
      scheduleDeparture(leg.updated_at, 20, 25, "BL"),
    ];
    return result;
  });
  assert.equal(f.planner._activeRouteId, "direct-blue");
  const buttons =
    f.planner._board.shadowRoot.querySelectorAll(".origin-choice");
  assert.equal(buttons.length, 8);
  assert.equal(buttons[7].getAttribute("aria-pressed"), "true");
  assert.match(buttons[7].textContent, /Recommended train/);
  assert.match(buttons[7].getAttribute("aria-label"), /20 minutes/);
});
