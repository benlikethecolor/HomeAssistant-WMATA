const WMATA_APPEARANCES = [
  { value: "standard", label: "Standard" },
  { value: "native", label: "Home Assistant" },
  { value: "minimal", label: "Minimal" },
  { value: "mushroom", label: "Mushroom-inspired" },
  { value: "glass", label: "Glass" },
  { value: "daylight", label: "Daylight" },
  { value: "orbit", label: "Orbit" },
  { value: "bento", label: "Bento" },
];
const validAppearance = (value) =>
  WMATA_APPEARANCES.some((option) => option.value === value);

/* WMATA Station Board 4.0.0 — no external libraries or network requests. */
(() => {
  const COLORS = {
    BL: ["Blue", "#0076be", "#fff"],
    GR: ["Green", "#008344", "#fff"],
    OR: ["Orange", "#c85100", "#fff"],
    RD: ["Red", "#b9222c", "#fff"],
    SV: ["Silver", "#adb3b8", "#182029"],
    YL: ["Yellow", "#f6d54b", "#182029"],
  };
  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  };
  const isList = (v) =>
    Array.isArray(v) && v.every((x) => typeof x === "string");
  const routeKey = (a) => a.line || a.route || "OTHER";
  const destinationKey = (a) =>
    a.destination_code || a.destination || "Unknown destination";
  const emit = (target, name, detail) =>
    target.dispatchEvent(
      new CustomEvent(name, {
        detail,
        bubbles: true,
        composed: true,
      }),
    );
  const STYLE = `
    .trip-itinerary{list-style:none;margin:12px 0 0;padding:0}.trip-itinerary li{border-top:1px solid var(--divider-color,#ddd);padding:10px 0;font-size:12px;line-height:1.6}.trip-itinerary strong{font-weight:650}.trip-itinerary small{display:block;color:var(--secondary-text-color,#64717b)}.schedule-tag{color:var(--warning-color,#9a660d)}.arrival[data-connection=likely][data-source=schedule]{background:color-mix(in srgb,var(--warning-color,#bb8500) 13%,transparent)}.arrival[data-connection=likely][data-source=schedule] .connection-label{color:var(--warning-color,#9a660d)}.departure-clock{font-size:11px;color:var(--secondary-text-color,#64717b);margin-top:4px}
    .origin-choice,.origin-reset{font:inherit;font-size:11px;border:1px solid var(--divider-color,#ccc);border-radius:8px;padding:5px 8px;background:transparent;color:inherit;cursor:pointer;margin-top:7px}.origin-choice[aria-pressed=true]{border-color:var(--primary-color,#0076be);background:color-mix(in srgb,var(--primary-color,#0076be) 12%,transparent)}.origin-choice:disabled{opacity:.5;cursor:default}.origin-selection{padding:0 22px 12px;font-size:12px;color:var(--secondary-text-color,#64717b)}
    .journey-eta{margin:0 22px 16px;padding:12px;border:1px solid var(--divider-color,#e2e7eb);border-radius:12px}.journey-eta-heading{font-size:12px;color:var(--secondary-text-color,#64717b);margin-bottom:5px}.journey-eta-time{font-size:22px;font-weight:650;line-height:1.4}.journey-eta-details{font-size:11px;line-height:1.6;color:var(--secondary-text-color,#64717b);margin-top:4px}
    .connection-summary{font-size:12px;line-height:1.6;margin:0 0 10px;color:var(--secondary-text-color,#64717b)}.connection-label{font-size:11px;font-weight:600;margin-top:5px}.arrival[data-connection=likely]{background:color-mix(in srgb,var(--success-color,#278057) 12%,transparent);border-radius:8px;padding-left:8px;padding-right:8px}.arrival[data-connection=likely] .connection-label{color:var(--success-color,#278057)}.arrival[data-connection=early] .connection-label{color:var(--secondary-text-color,#64717b)}
    .leg-heading{padding:0 22px 12px;font-size:13px;font-weight:600;line-height:1.5}.journey-transfers{border-top:1px solid var(--divider-color,#e2e7eb);padding:16px 22px}.transfer-note{font-size:12px;line-height:1.5;color:var(--secondary-text-color,#64717b);margin:0 0 14px}.transfer-station{margin-top:16px}.transfer-title{font-size:14px;font-weight:600;line-height:1.5;margin:0 0 8px}.transfer-status,.transfer-updated{font-size:11px;color:var(--secondary-text-color,#64717b);line-height:1.5}.transfer-updated{margin-top:8px}.transfer-updated[data-stale=true]{color:var(--warning-color,#9a660d)}
    .journey-route{margin:0 22px 14px;padding:12px;border-radius:12px;background:var(--secondary-background-color,#eff3f5);font-size:13px;line-height:1.5}.journey-route small{display:block;margin-top:4px;color:var(--secondary-text-color,#64717b)}
    :host([data-appearance=native]){font-family:var(--ha-font-family-body,Roboto,system-ui,sans-serif)}
    :host([data-appearance=native]) ha-card{border-radius:var(--ha-card-border-radius,12px);box-shadow:var(--ha-card-box-shadow,none);border-width:var(--ha-card-border-width,1px);border-color:var(--ha-card-border-color,var(--divider-color,#e0e0e0));background:var(--ha-card-background,var(--card-background-color,#fff))}
    :host([data-appearance=native]) .header{padding:16px;gap:8px}:host([data-appearance=native]) .mark{background:none;width:32px;height:32px}:host([data-appearance=native]) .eyebrow{display:none}:host([data-appearance=native]) .title{font-size:20px;font-weight:400;letter-spacing:normal}:host([data-appearance=native]) .number{font-weight:400}:host([data-appearance=native]) .filters,:host([data-appearance=native]) .rows{padding-left:16px;padding-right:16px}
    :host([data-appearance=minimal]) ha-card{border:0;border-radius:var(--ha-card-border-radius,12px);box-shadow:none}:host([data-appearance=minimal]) .header{padding:16px 16px 12px}:host([data-appearance=minimal]) .mark,:host([data-appearance=minimal]) .eyebrow,:host([data-appearance=minimal]) .columns{display:none}:host([data-appearance=minimal]) .title{font-size:18px;font-weight:500}:host([data-appearance=minimal]) .arrival{padding:10px 0}:host([data-appearance=minimal]) .number{font-size:25px;font-weight:500}
    :host([data-appearance=mushroom]) ha-card{border-radius:28px;box-shadow:var(--ha-card-box-shadow,none)}:host([data-appearance=mushroom]) .header{padding:16px;gap:12px}:host([data-appearance=mushroom]) .mark{border-radius:50%;width:48px;height:48px;background:var(--secondary-background-color,#f0f2f4)}:host([data-appearance=mushroom]) .title{font-size:19px;font-weight:500}:host([data-appearance=mushroom]) .chip{border-radius:20px}:host([data-appearance=mushroom]) .badge{border-radius:16px}:host([data-appearance=mushroom]) .number{font-weight:500}
    :host([data-appearance=glass]) ha-card{background:var(--ha-card-background,var(--card-background-color,#fff));background:color-mix(in srgb,var(--ha-card-background,var(--card-background-color,#fff)) 78%,transparent);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:1px solid color-mix(in srgb,var(--primary-text-color,#222) 14%,transparent);border-radius:24px;box-shadow:0 8px 32px #0001}

    :host{display:block;color:var(--primary-text-color,#202b35);font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif)}
    :host([data-appearance=orbit]),:host([data-appearance=bento]),:host([data-appearance=daylight]){--ha-card-background:#18212c;--secondary-background-color:#253140;--primary-text-color:#f5f4f1;--secondary-text-color:#b1bac5;--divider-color:#394452;--ha-card-border-radius:24px;font-family:Inter,system-ui,sans-serif}
    :host([data-appearance=bento]){--ha-card-background:#16171c;--secondary-background-color:#28292c;--divider-color:#38393c;font-family:Manrope,system-ui,sans-serif}
    :host([data-appearance=daylight]) .title,:host([data-appearance=daylight]) .planner-title{font-family:Fraunces,Georgia,serif;font-weight:400;font-size:28px}
    :host([data-appearance=daylight]){--primary-color:#cc8c51}:host([data-appearance=daylight][data-day=true]){--ha-card-background:#edf3fa;--secondary-background-color:#e1e8f0;--primary-text-color:#23324a;--secondary-text-color:#596b83;--divider-color:#cdd9e7;--primary-color:#aa632b}
    *{box-sizing:border-box}ha-card{display:block;overflow:hidden;background:var(--ha-card-background,var(--card-background-color,#fff));border-radius:var(--ha-card-border-radius,20px);border:1px solid var(--divider-color,#e2e7eb)}
    .header{padding:22px 22px 16px;display:flex;align-items:center;gap:13px}.mark{display:grid;place-items:center;width:43px;height:43px;flex-shrink:0;border-radius:14px;background:var(--secondary-background-color,#eff3f5)}
    .mark ha-icon{--mdc-icon-size:24px}.heading{flex:1;min-width:0}.eyebrow{font-size:10px;font-weight:750;letter-spacing:1.5px;color:var(--secondary-text-color,#64717b);margin-bottom:5px}
    .title{display:block;padding:0;border:0;background:none;color:inherit;font:inherit;font-size:21px;font-weight:730;letter-spacing:-.5px;text-align:left;cursor:pointer;overflow-wrap:anywhere}
    button:focus-visible,select:focus-visible{outline:2px solid var(--primary-color,#0076be);outline-offset:3px}.live{display:flex;align-items:center;gap:5px;font-size:10px;letter-spacing:.8px;font-weight:750;color:var(--secondary-text-color,#64717b)}
    .dot{width:6px;height:6px;border-radius:50%;background:#278057}.live[data-stale=true] .dot{background:#be7c0c}.live[data-stale=true]{color:var(--warning-color,#9a660d)}
    .filters{padding:0 22px 14px}.chips{display:flex;gap:7px;overflow-x:auto;padding:3px 2px 6px;scrollbar-width:thin}
    .chip{display:flex;align-items:center;gap:6px;white-space:nowrap;border:1px solid var(--divider-color,#dfe5e8);border-radius:30px;padding:7px 11px;background:transparent;color:inherit;font:inherit;font-size:12px;font-weight:600;cursor:pointer}
    .chip[aria-pressed=true]{background:var(--secondary-background-color,#eef3f5);border-color:var(--primary-text-color,#263743)}.swatch{width:8px;height:8px;border-radius:50%;background:var(--line-color,#687b89)}
    .destination-filter{display:block;width:100%;margin-top:5px;padding:9px 11px;font:inherit;font-size:12px;color:inherit;border-radius:10px;border:1px solid var(--divider-color,#dfe5e8);background:var(--ha-card-background,var(--card-background-color,#fff));min-width:0}
    .columns{display:flex;justify-content:space-between;padding:0 22px 10px;color:var(--secondary-text-color,#64717b);font-size:10px;font-weight:700;letter-spacing:1.1px}
    .rows{padding:0 22px}.arrival{display:grid;grid-template-columns:64px minmax(0,1fr) auto;gap:12px;align-items:center;padding:15px 0;border-top:1px solid var(--divider-color,#e6ebee)}
    .badge{border-radius:8px;padding:7px 6px;text-align:center;font-size:11px;font-weight:750;background:var(--line-color,#526774);color:var(--line-text,#fff);overflow-wrap:anywhere}
    .destination{font-size:15px;line-height:1.3;font-weight:650;overflow-wrap:anywhere}.details{font-size:11px;line-height:1.4;color:var(--secondary-text-color,#64717b);margin-top:4px}
    .eta{text-align:right;white-space:nowrap}.number{font-variant-numeric:tabular-nums;font-size:28px;line-height:1;font-weight:700;letter-spacing:-1px}.unit{font-size:10px;color:var(--secondary-text-color,#64717b);margin-left:4px}.status{font-size:11px;font-weight:750;color:var(--secondary-text-color,#64717b)}
    .status.imminent{color:var(--primary-text-color,#202b35);background:color-mix(in srgb,#21a365 16%,transparent);padding:4px 6px;border-radius:6px}.message{padding:30px 22px 35px;text-align:center;color:var(--secondary-text-color,#64717b);font-size:13px;line-height:1.6}
    .footer{display:flex;flex-wrap:wrap;gap:8px;justify-content:space-between;margin:0 22px;padding:13px 0 17px;border-top:1px solid var(--divider-color,#e6ebee);font-size:10px;color:var(--secondary-text-color,#64717b)}
    .footer[data-stale=true] .updated{color:var(--warning-color,#9a660d)}
    @media(max-width:340px){.header{padding:18px 15px 14px}.filters,.rows{padding-left:15px;padding-right:15px}.columns{padding-left:15px;padding-right:15px}.footer{margin:0 15px}.arrival{grid-template-columns:53px minmax(0,1fr) auto;gap:9px}.title{font-size:19px}.number{font-size:25px}.destination{font-size:13px}}
  `;

  class WmataStationCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._line = "all";
      this._destination = "all";
    }
    setConfig(config) {
      if (
        !config ||
        typeof config.entity !== "string" ||
        !config.entity.startsWith("sensor.")
      )
        throw new Error("Choose a WMATA arrivals or journey sensor.");
      if (
        config.max_rows !== undefined &&
        (!Number.isInteger(config.max_rows) ||
          config.max_rows < 1 ||
          config.max_rows > 30)
      )
        throw new Error("max_rows must be an integer between 1 and 30.");
      for (const key of ["lines", "routes", "destinations"])
        if (config[key] !== undefined && !isList(config[key]))
          throw new Error(`${key} must be a list of strings.`);
      if (
        config.transfer_rows !== undefined &&
        (!Number.isInteger(config.transfer_rows) ||
          config.transfer_rows < 1 ||
          config.transfer_rows > 10)
      )
        throw new Error("transfer_rows must be an integer between 1 and 10.");
      for (const key of ["show_transfer_predictions", "show_destination_eta"])
        if (config[key] !== undefined && typeof config[key] !== "boolean")
          throw new Error(`${key} must be true or false`);
      if (
        config.transfer_buffer !== undefined &&
        (!Number.isInteger(config.transfer_buffer) ||
          config.transfer_buffer < 1 ||
          config.transfer_buffer > 30)
      )
        throw new Error(
          "transfer_buffer must be an integer between 1 and 30 minutes.",
        );
      if (this._config?.entity !== config.entity) {
        this._stopTransferPolling();
        this._originSelection = null;
        this._line = "all";
        this._destination = "all";
      }
      if (
        config.appearance !== undefined &&
        !validAppearance(config.appearance)
      )
        throw new Error("Choose a supported appearance preset.");
      this.dataset.appearance = config.appearance || "standard";
      this._config = {
        max_rows: 8,
        show_filters: true,
        show_updated: true,
        show_transfer_predictions: true,
        show_destination_eta: true,
        transfer_rows: 3,
        transfer_buffer: 3,
        ...config,
      };
      this._render();
    }
    set hass(hass) {
      const before = this._hass?.states?.[this._config?.entity];
      this.dataset.day = String(
        hass?.states?.["sun.sun"]?.state === "above_horizon",
      );
      this._hass = hass;
      if (
        before !== hass?.states?.[this._config?.entity] ||
        !this.shadowRoot.firstChild
      )
        this._render();
    }
    connectedCallback() {
      if (!this._timer)
        this._timer = setInterval(() => this._updateFreshness(), 15000);
      this._render();
    }
    disconnectedCallback() {
      clearInterval(this._timer);
      this._timer = null;
      this._stopTransferPolling();
    }
    getCardSize() {
      const transfers = this._config?.show_transfer_predictions
        ? Math.max(0, (this._transferRoute()?.legs?.length || 1) - 1)
        : 0;
      return (
        2 +
        (this._config?.show_destination_eta &&
        this._transferRoute()?.legs?.length
          ? 2
          : 0) +
        (this._config?.max_rows || 8) +
        transfers * (2 + (this._config?.transfer_rows || 3))
      );
    }
    getGridOptions() {
      return { columns: 12, min_columns: 6 };
    }
    static getConfigElement() {
      return document.createElement("wmata-station-card-editor");
    }
    static getStubConfig(hass) {
      const entity = Object.keys(hass?.states || {}).find(
        (id) => hass.states[id].attributes?.board_type === "station",
      );
      return {
        type: "custom:wmata-station-card",
        entity: entity || "",
        max_rows: 8,
      };
    }
    _moreInfo() {
      emit(this, "hass-more-info", { entityId: this._config.entity });
    }
    _configuredArrivals(state) {
      const all = Array.isArray(state?.attributes?.arrivals)
        ? state.attributes.arrivals.filter((a) => a && typeof a === "object")
        : [];
      const origin = this._transferData?.find((leg) => leg.index === 0);
      return this._mergeArrivals(
        all,
        this._transferRoute()?.legs?.length ? origin : null,
        state?.attributes?.updated_at,
      ).filter(
        (a) =>
          (!this._config.lines?.length ||
            this._config.lines.includes(a.line)) &&
          (!this._config.routes?.length ||
            this._config.routes.includes(a.route)) &&
          (!this._config.destinations?.length ||
            this._config.destinations.includes(a.destination_code)),
      );
    }
    _badge(node, key, text) {
      const colors = COLORS[key] || [text || key, "#526774", "#fff"];
      node.style.setProperty("--line-color", colors[1]);
      node.style.setProperty("--line-text", colors[2]);
      return node;
    }
    _transferRoute() {
      return this._hass?.states?.[this._config?.entity]?.attributes
        ?.journey_route;
    }
    _routeKey() {
      return JSON.stringify([
        this._config?.entity,
        this._transferRoute()?.legs?.map((leg) => [leg.from, leg.to]),
      ]);
    }
    _originSignature(arrival) {
      return JSON.stringify([
        arrival.prediction_source || "live",
        arrival.line,
        destinationKey(arrival),
        arrival.group || "",
        arrival.cars || "",
      ]);
    }
    _selectOrigin(arrival) {
      const state = this._hass.states[this._config.entity];
      this._originSelection = {
        route: this._routeKey(),
        signature: this._originSignature(arrival),
        departure: this._departureAt(arrival, state.attributes.updated_at),
      };
      this._render();
    }
    setJourneyPreview(hass, result, config) {
      this._preview = true;
      const oldRoute = this._routeKey();
      this.setConfig({ ...config, entity: "sensor.wmata_trip_preview" });
      this._transferData = result.legs;
      this._transferError = false;
      const origin = result.legs[0];
      this.hass = {
        ...hass,
        states: {
          ...hass.states,
          "sensor.wmata_trip_preview": {
            state: String(origin.arrivals[0]?.minutes ?? "unknown"),
            attributes: {
              schema_version: 1,
              board_type: "journey",
              service_type: "train",
              journey_name: "To " + result.route.destination_name,
              journey_route: result.route,
              route_description: result.route_description,
              arrivals: origin.arrivals,
              updated_at: origin.updated_at,
            },
          },
        },
      };
      if (oldRoute !== this._routeKey()) {
        this._originSelection = null;
        this._render();
      }
    }
    _stopTransferPolling() {
      clearInterval(this._transferTimer);
      this._transferTimer = null;
      this._transferGeneration = (this._transferGeneration || 0) + 1;
      this._transferKey = null;
      this._transferPending = false;
      this._transferData = null;
      this._transferError = false;
    }
    _syncTransferPolling() {
      if (this._preview) {
        clearInterval(this._transferTimer);
        this._transferTimer = null;
        return;
      }
      const route = this._transferRoute();
      if (
        !this.isConnected ||
        !(route?.legs?.length > 0) ||
        (!this._config?.show_destination_eta &&
          !(
            this._config?.show_transfer_predictions && route.legs.length > 1
          )) ||
        typeof this._hass?.callWS !== "function"
      ) {
        this._stopTransferPolling();
        return;
      }
      const key = JSON.stringify([
        this._config.entity,
        route.legs.map((leg) => [leg.from, leg.to]),
      ]);
      if (key !== this._transferKey) {
        this._stopTransferPolling();
        this._transferKey = key;
        this._renderTransfers();
        this._fetchTransfers();
      }
      if (!this._transferTimer)
        this._transferTimer = setInterval(() => this._fetchTransfers(), 30000);
    }
    async _fetchTransfers() {
      if (
        this._transferPending ||
        !this.isConnected ||
        !this._transferKey ||
        document.visibilityState === "hidden"
      )
        return;
      const generation = this._transferGeneration;
      const key = this._transferKey;
      this._transferPending = true;
      try {
        const result = await this._hass.callWS({
          type: "wmata/journey_arrivals",
          entity_id: this._config.entity,
        });
        if (
          generation !== this._transferGeneration ||
          key !== this._transferKey ||
          !this.isConnected
        )
          return;
        if (!Array.isArray(result.legs))
          throw new Error("Missing journey predictions");
        this._transferData = result.legs;
        this._transferError = false;
      } catch {
        if (
          generation !== this._transferGeneration ||
          key !== this._transferKey ||
          !this.isConnected
        )
          return;
        this._transferError = true;
      } finally {
        if (generation === this._transferGeneration && this.isConnected) {
          this._transferPending = false;
          this._render();
        }
      }
    }
    _renderTransfers() {
      const previous = this.shadowRoot.querySelector(".journey-transfers");
      const route = this._transferRoute();
      const connections = this._connectionPlan();
      this._renderDestination(connections);
      if (
        !this._config?.show_transfer_predictions ||
        !(route?.legs?.length > 1)
      ) {
        previous?.remove();
        return;
      }
      const card = this.shadowRoot.querySelector("ha-card");
      if (!card) return;
      const section = element("section", "journey-transfers");
      section.setAttribute("aria-label", "Live transfer predictions");
      section.append(
        element(
          "p",
          "transfer-note",
          "Live departures are used first; later connections use clearly labeled timetable estimates. Allow " +
            this._config.transfer_buffer +
            " min to change platforms. Estimates are not guaranteed; delays can change them.",
        ),
      );
      if (connections.origin) {
        section.append(
          element(
            "p",
            "connection-summary",
            `Based on ${COLORS[connections.origin.line]?.[0] || "the next train"} to ${connections.origin.destination || route.legs[0].to_name} at ${this._clock(connections.departure)} from ${route.origin_name}.`,
          ),
        );
      }
      route.legs.slice(1).forEach((leg, index) => {
        const live = this._transferData?.find(
          (value) => value.index === index + 1,
        );
        const arrivals = this._legArrivals(live);
        const station = element("section", "transfer-station");
        station.append(
          element(
            "h3",
            "transfer-title",
            `Leg ${index + 2} · ${leg.from_name} → ${leg.to_name}`,
          ),
        );
        const estimate = connections.legs[index];
        station.append(
          element(
            "p",
            "connection-summary",
            estimate?.ready
              ? `Reach ${leg.from_name} about ${this._clock(estimate.reach)} · ready to board ${this._clock(estimate.ready)} (${this._config.transfer_buffer} min to change).`
              : "Connection estimate unavailable. " +
                  (estimate?.reason || "Waiting for live predictions."),
          ),
        );
        if (
          this._transferError ||
          (live && !live.available && !arrivals.length) ||
          (!this._preview && typeof this._hass?.callWS !== "function")
        ) {
          station.append(
            element(
              "div",
              "transfer-status",
              "Predictions temporarily unavailable. Retrying shortly.",
            ),
          );
        } else if (!live)
          station.append(
            element("div", "transfer-status", "Loading current predictions…"),
          );
        else if (!arrivals.length)
          station.append(
            element(
              "div",
              "transfer-status",
              "No matching trains are currently predicted.",
            ),
          );
        else {
          const rows = element("div", "transfer-arrivals");
          rows.setAttribute("role", "list");
          rows.setAttribute("aria-label", leg.from_name + " departures");
          const shown = arrivals.slice(0, this._config.transfer_rows);
          // Keep the first likely connection visible even when earlier trains fill the row limit.
          if (estimate?.chosen && !shown.includes(estimate.chosen))
            shown[shown.length - 1] = estimate.chosen;
          shown.forEach((arrival) => {
            const row = this._row(arrival);
            row.dataset.source = arrival.prediction_source || "live";
            if (arrival.prediction_source !== "schedule") {
              const timestamp = this._departureAt(arrival, live.updated_at);
              if (timestamp !== null)
                row
                  .querySelector(".destination")
                  .parentElement.append(
                    element(
                      "div",
                      "departure-clock",
                      "Live · expected " + this._clock(timestamp),
                    ),
                  );
            }
            const status = estimate?.statuses.get(arrival) || "unknown";
            row.dataset.connection = status;
            row
              .querySelector(".destination")
              .parentElement.append(
                element(
                  "div",
                  "connection-label",
                  status === "likely"
                    ? arrival.prediction_source === "schedule"
                      ? "Schedule estimate · possible connection"
                      : arrival === estimate.chosen
                        ? "Suggested connection"
                        : "Also likely catchable"
                    : status === "early"
                      ? "Too early for this connection"
                      : "Connection unknown",
                ),
              );
            rows.append(row);
          });
          station.append(rows);
          if (estimate?.ready && !estimate.chosen && !estimate.stale)
            station.append(
              element(
                "p",
                "connection-summary",
                "No catchable trains in the current prediction window. Later departures may appear on refresh.",
              ),
            );
        }
        if (live?.updated_at && this._config.show_updated) {
          const updated = element("div", "transfer-updated");
          updated.dataset.updatedAt = live.updated_at;
          station.append(updated);
        }
        section.append(station);
      });
      if (previous) previous.replaceWith(section);
      else card.append(section);
      this._updateTransferAges();
    }
    _clock(timestamp) {
      return new Date(timestamp).toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit",
      });
    }
    _renderDestination(plan) {
      const previous = this.shadowRoot.querySelector(".journey-eta");
      const route = this._transferRoute();
      if (!this._config?.show_destination_eta || !route?.legs?.length) {
        previous?.remove();
        return;
      }
      const card = this.shadowRoot.querySelector("ha-card");
      if (!card) return;
      const section = element("section", "journey-eta");
      section.setAttribute("aria-label", "Estimated destination arrival");
      section.append(
        element(
          "div",
          "journey-eta-heading",
          (plan.schedule_estimate
            ? "Schedule-based arrival · "
            : "Estimated arrival · ") +
            (route.destination_name || route.legs.at(-1).to_name),
        ),
      );
      if (Number.isFinite(plan.arrival)) {
        section.append(
          element(
            "div",
            "journey-eta-time",
            "About " + this._clock(plan.arrival),
          ),
        );
        const minutes = Math.max(
          0,
          Math.ceil((plan.arrival - Date.now()) / 60000),
        );
        section.append(
          element(
            "div",
            "journey-eta-details",
            `About ${minutes} min from now · includes the wait for the first train, all rides${route.legs.length > 1 ? ", transfer waits, and " + this._config.transfer_buffer + " min to switch platforms at each transfer" : ""}.`,
          ),
        );
        section.append(
          element(
            "div",
            "journey-eta-details trip-total",
            `Station-to-station: about ${Math.round(plan.trip_minutes)} min · ${Math.round(plan.ride_minutes)} min riding${route.legs.length > 1 ? ", " + plan.platform_minutes + " min switching, " + Math.round(plan.transfer_wait_minutes) + " min waiting for connections" : ""}.`,
          ),
        );
        section.append(
          element(
            "div",
            "journey-eta-details",
            "Based on " +
              (this._originSelection
                ? "your selected origin train"
                : "the next matching origin train") +
              " and scheduled ride times. Delays can change this estimate.",
          ),
        );
      } else {
        section.append(
          element(
            "div",
            "journey-eta-details",
            !this._transferData &&
              !this._transferError &&
              typeof this._hass?.callWS === "function"
              ? "Loading journey estimate…"
              : "Arrival estimate unavailable. " + plan.arrival_reason,
          ),
        );
      }
      if (plan.itinerary?.length) {
        const itinerary = element("ol", "trip-itinerary");
        itinerary.setAttribute("aria-label", "Predicted journey timeline");
        plan.itinerary.forEach((leg, index) => {
          const row = element("li");
          row.append(
            element("strong", null, `${leg.from_name} → ${leg.to_name}`),
          );
          row.append(
            element(
              "small",
              null,
              leg.departure !== null && leg.arrival !== null
                ? `Board ${this._clock(leg.departure)} · ride ${Math.round(leg.ride_minutes)} min · arrive about ${this._clock(leg.arrival)}`
                : "Boarding or arrival time not available yet.",
            ),
          );
          if (leg.train)
            row.append(
              element(
                "small",
                leg.train.prediction_source === "schedule"
                  ? "schedule-tag"
                  : null,
                `${leg.train.line_name || COLORS[leg.train.line]?.[0] || "Train"} to ${leg.train.destination || leg.to_name} · ${leg.train.prediction_source === "schedule" ? "Timetable estimate, not live" : "Live departure + estimated ride"}`,
              ),
            );
          if (index > 0 && plan.legs[index - 1]?.ready) {
            const transfer = plan.legs[index - 1];
            row.append(
              element(
                "small",
                null,
                `Ready to board ${this._clock(transfer.ready)} · ${this._config.transfer_buffer} min switching platforms${transfer.wait_minutes !== null && transfer.wait_minutes !== undefined ? " + " + Math.round(transfer.wait_minutes) + " min waiting" : ""}`,
              ),
            );
          }
          itinerary.append(row);
        });
        section.append(itinerary);
      }
      if (previous) previous.replaceWith(section);
      else {
        const instructions = card.querySelector(".journey-route");
        if (instructions) instructions.after(section);
        else card.querySelector(".header")?.after(section);
      }
    }
    _departureAt(arrival, updatedAt) {
      if (arrival.prediction_source === "schedule") {
        const value = Date.parse(arrival.departure_at);
        return Number.isFinite(value) ? value : null;
      }
      if (
        !Number.isFinite(arrival.minutes) ||
        arrival.minutes < 0 ||
        !["predicted", "arriving", "boarding"].includes(arrival.status)
      )
        return null;
      const value = Date.parse(updatedAt) + arrival.minutes * 60000;
      return Number.isFinite(value) ? value : null;
    }
    _fresh(data) {
      const timestamp = Date.parse(data?.updated_at);
      return (
        Number.isFinite(timestamp) &&
        Date.now() - timestamp <= 90000 &&
        timestamp <= Date.now() + 30000
      );
    }
    _mergeArrivals(arrivals, data, updatedAt) {
      const now = Date.now();
      const windows = new Map();
      if (this._fresh({ updated_at: updatedAt }))
        for (const arrival of arrivals) {
          const time = this._departureAt(arrival, updatedAt);
          if (time !== null)
            windows.set(
              arrival.line,
              Math.max(windows.get(arrival.line) || 0, time),
            );
        }
      const scheduled = this._transferError
        ? []
        : (data?.scheduled_departures || []).filter((arrival) => {
            const timestamp = Date.parse(arrival.departure_at);
            if (
              !Number.isFinite(timestamp) ||
              timestamp < now ||
              timestamp <= (windows.get(arrival.line) || 0) + 60000
            )
              return false;
            arrival.minutes = Math.ceil((timestamp - now) / 60000);
            return true;
          });
      return [...arrivals, ...scheduled].sort(
        (a, b) =>
          (this._departureAt(a, updatedAt) ?? Infinity) -
          (this._departureAt(b, updatedAt) ?? Infinity),
      );
    }
    _legArrivals(data) {
      return this._mergeArrivals(data?.arrivals || [], data, data?.updated_at);
    }
    _rideArrival(train, departure, live) {
      if (departure === null) return null;
      if (train?.prediction_source === "schedule") {
        const arrival = Date.parse(train.arrival_at);
        if (Number.isFinite(arrival) && arrival > departure) return arrival;
      }
      return Number.isFinite(live?.ride_minutes) && live.ride_minutes > 0
        ? departure + live.ride_minutes * 60000
        : null;
    }
    _connectionPlan() {
      const now = Date.now();
      const state = this._hass?.states?.[this._config?.entity];
      const route = this._transferRoute();
      const origins = this._configuredArrivals(state)
        .filter(
          (a) =>
            (a.prediction_source === "schedule" ||
              (state?.state !== "unavailable" &&
                this._fresh(state?.attributes))) &&
            (this._line === "all" || routeKey(a) === this._line) &&
            (this._destination === "all" ||
              destinationKey(a) === this._destination),
        )
        .map((arrival) => ({
          arrival,
          time: this._departureAt(arrival, state?.attributes?.updated_at),
        }))
        .filter((value) => value.time !== null && value.time >= now - 30000)
        .sort((a, b) => a.time - b.time);
      if (this._originSelection?.route !== this._routeKey())
        this._originSelection = null;
      let selected = origins[0];
      if (this._originSelection) {
        const matches = origins
          .filter(
            (value) =>
              this._originSignature(value.arrival) ===
              this._originSelection.signature,
          )
          .map((value) => ({
            ...value,
            difference: Math.abs(value.time - this._originSelection.departure),
          }))
          .sort((a, b) => a.difference - b.difference);
        selected =
          matches[0]?.difference <= 90000 &&
          matches[0]?.difference !== matches[1]?.difference
            ? matches[0]
            : undefined;
      }
      const result = {
        origin: selected?.arrival,
        departure: selected ? Math.max(now, selected.time) : null,
        legs: [],
        itinerary: [],
        schedule_estimate: selected?.arrival.prediction_source === "schedule",
      };
      let boarded = result.departure;
      let train = result.origin;
      let reason = "No fresh origin departure is available.";
      for (let i = 0; i < (route?.legs?.length || 0); i++) {
        const leg = route.legs[i];
        const live = this._transferData?.find((value) => value.index === i);
        const reach = this._rideArrival(train, boarded, live);
        result.itinerary.push({
          from_name: leg.from_name,
          to_name: leg.to_name,
          lines: leg.lines,
          train,
          departure: boarded,
          arrival: reach,
          ride_minutes:
            reach !== null && boarded !== null
              ? (reach - boarded) / 60000
              : null,
        });
        if (i === route.legs.length - 1) {
          if (!this._transferError && reach !== null) result.arrival = reach;
          break;
        }
        const next = this._transferData?.find((value) => value.index === i + 1);
        const estimate = { statuses: new Map(), reason };
        if (reach !== null) {
          estimate.reach = reach;
          estimate.ready = reach + this._config.transfer_buffer * 60000;
        } else if (boarded !== null)
          estimate.reason = "Scheduled ride time is unavailable.";
        const available = this._legArrivals(next);
        const scheduleExists = available.some(
          (a) => a.prediction_source === "schedule",
        );
        estimate.stale =
          this._transferError ||
          ((!next?.available || !this._fresh(next)) && !scheduleExists);
        if (estimate.ready && !estimate.stale) {
          const candidates = [];
          for (const arrival of available) {
            const time = this._departureAt(arrival, next?.updated_at);
            const usable =
              arrival.prediction_source === "schedule" ||
              (next?.available && this._fresh(next));
            const status =
              !usable || time === null
                ? "unknown"
                : time >= estimate.ready && time >= now
                  ? "likely"
                  : "early";
            estimate.statuses.set(arrival, status);
            if (status === "likely") candidates.push({ arrival, time });
          }
          candidates.sort((a, b) => a.time - b.time);
          estimate.chosen = candidates[0]?.arrival;
          estimate.departure = candidates[0]?.time ?? null;
          estimate.wait_minutes =
            estimate.departure === null
              ? null
              : (estimate.departure - estimate.ready) / 60000;
          boarded = estimate.departure;
          train = estimate.chosen;
          if (train?.prediction_source === "schedule")
            result.schedule_estimate = true;
          reason = "No catchable train is predicted for the preceding leg yet.";
        } else {
          boarded = null;
          train = null;
          reason = "The preceding connection has no reliable estimate.";
        }
        result.legs.push(estimate);
      }
      if (!Number.isFinite(result.arrival))
        result.arrival_reason = this._transferError
          ? "Journey predictions are temporarily unavailable."
          : !result.origin
            ? this._originSelection
              ? "The selected train is no longer predicted. Choose another train or use the next train."
              : "No fresh origin departure is available."
            : result.legs.some((leg) => leg.stale)
              ? "Waiting for fresh transfer predictions."
              : result.legs.some((leg) => leg.ready && !leg.chosen)
                ? "No catchable connection is available in the current prediction window."
                : "Scheduled ride time is unavailable.";
      if (Number.isFinite(result.arrival)) {
        result.trip_minutes = (result.arrival - result.departure) / 60000;
        result.ride_minutes = result.itinerary.reduce(
          (sum, leg) => sum + leg.ride_minutes,
          0,
        );
        result.platform_minutes =
          result.legs.length * this._config.transfer_buffer;
        result.transfer_wait_minutes = result.legs.reduce(
          (sum, leg) => sum + (leg.wait_minutes || 0),
          0,
        );
      }
      return result;
    }
    _updateTransferAges() {
      this.shadowRoot.querySelectorAll(".transfer-updated").forEach((node) => {
        const timestamp = Date.parse(node.dataset.updatedAt);
        const age = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
        const stale = !Number.isFinite(timestamp) || age > 90;
        node.dataset.stale = String(stale);
        node.textContent = Number.isFinite(timestamp)
          ? `${stale ? "Stale · " : ""}Updated ${age < 10 ? "just now" : age < 60 ? age + "s ago" : Math.floor(age / 60) + "m ago"}`
          : "Update time unavailable";
        node.title = Number.isFinite(timestamp)
          ? new Date(timestamp).toLocaleString()
          : "";
      });
    }
    _render() {
      this._renderBoard();
      this._renderTransfers();
      this._syncTransferPolling();
    }
    _renderBoard() {
      if (!this._config) return;
      const state = this._hass?.states?.[this._config.entity];
      const attrs = state?.attributes || {};
      const compatible =
        Array.isArray(attrs.arrivals) && attrs.schema_version === 1;
      const arrivals = this._configuredArrivals(state);
      const offline =
        (!state || state.state === "unavailable") &&
        !arrivals.some((arrival) => arrival.prediction_source === "schedule");
      this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card></ha-card>`;
      const card = this.shadowRoot.querySelector("ha-card");
      const header = element("div", "header");
      const mark = element("div", "mark");
      const icon = element("ha-icon");
      icon.setAttribute(
        "icon",
        attrs.service_type === "bus" ? "mdi:bus" : "mdi:subway-variant",
      );
      mark.append(icon);
      const heading = element("div", "heading");
      heading.append(
        element(
          "div",
          "eyebrow",
          attrs.board_type === "journey"
            ? this._preview
              ? "TRIP PLAN"
              : "SAVED JOURNEY"
            : attrs.service_type === "bus"
              ? "METROBUS · ARRIVALS"
              : "METRORAIL · ARRIVALS",
        ),
      );
      const title = element(
        this._preview ? "h2" : "button",
        "title",
        this._config.title ||
          attrs.journey_name ||
          attrs.station_name ||
          "WMATA",
      );
      if (!this._preview) {
        title.type = "button";
        title.setAttribute(
          "aria-label",
          `Show details for ${title.textContent}`,
        );
        title.addEventListener("click", () => this._moreInfo());
      } else {
        title.style.margin = "0";
        title.style.cursor = "default";
      }
      heading.append(title);
      const live = element("div", "live");
      live.append(
        element("span", "dot"),
        element("span", "live-label", "LIVE"),
      );
      header.append(mark, heading, live);
      card.append(header);
      if (attrs.journey_route && attrs.route_description) {
        const route = element("div", "journey-route", attrs.route_description);
        route.append(
          element(
            "small",
            null,
            "Train countdowns below show time until boarding at " +
              attrs.journey_route.origin_name +
              ".",
          ),
        );
        card.append(route);
      }
      if (
        attrs.journey_route?.legs?.length > 1 &&
        this._config.show_transfer_predictions
      ) {
        const leg = attrs.journey_route.legs[0];
        card.append(
          element(
            "div",
            "leg-heading",
            `Leg 1 · ${attrs.journey_route.origin_name} → ${leg.to_name}`,
          ),
        );
      }
      if (offline || !compatible) {
        card.append(
          element(
            "div",
            "message",
            !state
              ? "Choose an available WMATA station board in the card editor."
              : offline
                ? "Arrival information is unavailable. Home Assistant will retry automatically."
                : "This entity is not a WMATA station board or journey sensor.",
          ),
        );
        live.dataset.stale = "true";
        live.querySelector(".live-label").textContent = "OFFLINE";
        return;
      }
      if (this._config.show_filters) {
        const filters = element("div", "filters");
        const chips = element("div", "chips");
        chips.setAttribute("role", "group");
        chips.setAttribute("aria-label", "Filter arrivals by line or route");
        const served =
          attrs.service_type === "train"
            ? this._config.lines?.length
              ? this._config.lines
              : attrs.served_lines || []
            : this._config.routes || [];
        const keys = [
          ...new Set([...arrivals.map(routeKey), ...served]),
        ].sort();
        if (this._line !== "all" && !keys.includes(this._line))
          keys.push(this._line);
        for (const key of ["all", ...keys]) {
          const label =
            key === "all"
              ? attrs.service_type === "bus"
                ? "All routes"
                : "All lines"
              : COLORS[key]?.[0] || key;
          const chip = element("button", "chip");
          chip.type = "button";
          chip.setAttribute("aria-pressed", String(this._line === key));
          if (key !== "all")
            chip.append(this._badge(element("span", "swatch"), key));
          chip.append(element("span", null, label));
          chip.addEventListener("click", () => {
            this._line = key;
            this._render();
          });
          chips.append(chip);
        }
        const select = element("select", "destination-filter");
        select.setAttribute("aria-label", "Filter arrivals by destination");
        const destinations = new Map(
          arrivals
            .filter((a) => this._line === "all" || routeKey(a) === this._line)
            .map((a) => [
              destinationKey(a),
              a.destination || "Unknown destination",
            ]),
        );
        if (this._destination !== "all" && !destinations.has(this._destination))
          destinations.set(
            this._destination,
            this._selectedDestinationLabel || this._destination,
          );
        const any = element("option", null, "All destinations");
        any.value = "all";
        select.append(any);
        for (const [key, label] of [...destinations].sort((a, b) =>
          a[1].localeCompare(b[1]),
        )) {
          const option = element("option", null, label);
          option.value = key;
          select.append(option);
        }
        select.value = this._destination;
        select.addEventListener("change", () => {
          this._destination = select.value;
          this._selectedDestinationLabel =
            select.selectedOptions[0]?.textContent;
          this._render();
        });
        filters.append(chips, select);
        card.append(filters);
      }
      const filtered = arrivals.filter(
        (a) =>
          (this._line === "all" || routeKey(a) === this._line) &&
          (this._destination === "all" ||
            destinationKey(a) === this._destination),
      );
      const shown = filtered.slice(0, this._config.max_rows);
      const journey = attrs.journey_route?.legs?.length > 0;
      const chosenOrigin = journey ? this._connectionPlan().origin : null;
      if (journey && this._originSelection) {
        const selection = element(
          "div",
          "origin-selection",
          chosenOrigin
            ? "Using your selected origin train. "
            : "Your selected train is no longer available. ",
        );
        const reset = element("button", "origin-reset", "Use next train");
        reset.type = "button";
        reset.onclick = () => {
          this._originSelection = null;
          this._render();
        };
        selection.append(reset);
        card.append(selection);
      }
      if (shown.length) {
        const columns = element("div", "columns");
        columns.append(
          element("span", null, "LINE / DESTINATION"),
          element("span", null, "DUE"),
        );
        card.append(columns);
        const rows = element("div", "rows");
        rows.setAttribute("role", "list");
        rows.setAttribute("aria-label", "Upcoming arrivals");
        for (const arrival of shown)
          rows.append(this._row(arrival, journey, arrival === chosenOrigin));
        card.append(rows);
      } else
        card.append(
          element(
            "div",
            "message",
            arrivals.length
              ? "No arrivals match these filters."
              : "No upcoming arrivals are currently predicted. Check back shortly.",
          ),
        );
      const footer = element("div", "footer");
      footer.append(
        element(
          "span",
          null,
          `${shown.length} of ${filtered.length} arrival${filtered.length === 1 ? "" : "s"}`,
        ),
      );
      if (this._config.show_updated) footer.append(element("span", "updated"));
      card.append(footer);
      this._updateFreshness();
    }
    _row(a, originChoice = false, selected = false) {
      const row = element("div", "arrival");
      row.setAttribute("role", "listitem");
      const key = routeKey(a);
      const label = COLORS[key]?.[0] || a.route || "Other";
      row.append(this._badge(element("div", "badge", label), key));
      const info = element("div");
      info.append(
        element(
          "div",
          "destination",
          a.destination || "Destination unavailable",
        ),
      );
      const details = [];
      if (a.prediction_source === "schedule")
        details.push(
          "Timetable estimate · expected " +
            this._clock(Date.parse(a.station_arrival_at || a.departure_at)) +
            (a.station_arrival_at && a.station_arrival_at !== a.departure_at
              ? " · boards " + this._clock(Date.parse(a.departure_at))
              : ""),
        );
      if (a.last_train) details.push("Last train");
      if (a.line) details.push(a.direction || "Direction unavailable");
      if (a.cars && a.cars !== "-") details.push(`${a.cars} cars`);
      if (a.vehicle_id) details.push(`Bus ${a.vehicle_id}`);
      if (details.length)
        info.append(element("div", "details", details.join(" · ")));
      if (originChoice) {
        const choose = element(
          "button",
          "origin-choice",
          selected
            ? this._originSelection
              ? "Selected train"
              : "Using next train"
            : "Use this train",
        );
        choose.type = "button";
        choose.setAttribute("aria-pressed", String(selected));
        choose.setAttribute(
          "aria-label",
          `Use ${label} to ${a.destination || "destination unavailable"} ${Number.isFinite(a.minutes) ? "in " + a.minutes + " minutes" : "with no estimate"}`,
        );
        choose.disabled =
          !Number.isFinite(a.minutes) ||
          !["predicted", "boarding", "arriving"].includes(a.status);
        choose.onclick = () => this._selectOrigin(a);
        info.append(choose);
      }
      const eta = element("div", "eta");
      if (a.status === "boarding" || a.status === "arriving") {
        eta.append(
          element(
            "span",
            "status imminent",
            a.status === "boarding" ? "Boarding" : "Arriving",
          ),
        );
      } else if (
        a.minutes !== null &&
        a.minutes !== undefined &&
        Number.isFinite(a.minutes)
      ) {
        eta.append(
          element("span", "number", a.minutes),
          element("span", "unit", "min"),
        );
      } else
        eta.append(
          element(
            "span",
            "status",
            a.status === "delayed" ? "Delayed" : "No estimate",
          ),
        );
      row.append(info, eta);
      return row;
    }
    _updateFreshness() {
      this._renderTransfers();
      const state = this._hass?.states?.[this._config?.entity];
      if (!state || state.state === "unavailable") return;
      const when = Date.parse(state.attributes.updated_at);
      const age = Math.max(0, Math.floor((Date.now() - when) / 1000));
      const stale =
        !Number.isFinite(when) ||
        age > Math.max(120, (Number(state.attributes.poll_interval) || 30) * 3);
      const live = this.shadowRoot.querySelector(".live");
      if (live) {
        live.dataset.stale = String(stale);
        live.querySelector(".live-label").textContent = stale
          ? "STALE"
          : "LIVE";
      }
      const footer = this.shadowRoot.querySelector(".footer");
      if (footer) footer.dataset.stale = String(stale);
      const updated = this.shadowRoot.querySelector(".updated");
      if (updated)
        updated.textContent = !Number.isFinite(when)
          ? "Update time unavailable"
          : `${stale ? "Stale · " : ""}Updated ${age < 10 ? "just now" : age < 60 ? `${age}s ago` : `${Math.floor(age / 60)}m ago`}`;
    }
  }

  class WmataStationCardEditor extends HTMLElement {
    setConfig(config) {
      this._config = {
        max_rows: 8,
        show_filters: true,
        show_updated: true,
        show_transfer_predictions: true,
        show_destination_eta: true,
        transfer_rows: 3,
        transfer_buffer: 3,
        ...config,
      };
      this._render();
    }
    set hass(hass) {
      this._hass = hass;
      this._render();
    }
    _render() {
      if (!this._config || !this._hass) return;
      if (!this._form) {
        this._form = document.createElement("ha-form");
        this.append(this._form);
        this._form.schema = [
          {
            name: "entity",
            required: true,
            selector: { entity: { domain: "sensor" } },
          },
          {
            name: "appearance",
            selector: {
              select: {
                options: WMATA_APPEARANCES,
                mode: "dropdown",
              },
            },
          },
          { name: "title", selector: { text: {} } },
          {
            name: "max_rows",
            selector: { number: { min: 1, max: 30, mode: "box" } },
          },
          { name: "show_filters", selector: { boolean: {} } },
          { name: "show_updated", selector: { boolean: {} } },
        ];
        this._form.computeLabel = ({ name }) =>
          ({
            entity: "Station board or journey",
            appearance: "Appearance",
            show_transfer_predictions: "Live transfer predictions",
            show_destination_eta: "Estimated arrival at destination",
            transfer_rows: "Trains per transfer",
            transfer_buffer: "Minutes to change platforms",
            title: "Title (optional)",
            max_rows: "Maximum arrivals",
            show_filters: "Show line and destination filters",
            show_updated: "Show update time",
          })[name] || name;
        this._form.addEventListener("value-changed", (event) => {
          event.stopPropagation();
          this._config = { ...this._config, ...event.detail.value };
          emit(this, "config-changed", { config: this._config });
        });
      }
      const choices = Object.entries(this._hass.states || {})
        .filter(
          ([id, state]) =>
            ["station", "journey"].includes(state.attributes?.board_type) ||
            id === this._config.entity,
        )
        .map(([value, state]) => ({
          value,
          label:
            state.attributes.friendly_name ||
            state.attributes.journey_name ||
            state.attributes.station_name ||
            value,
        }));
      this._form.schema = [
        {
          name: "entity",
          required: true,
          selector: { select: { options: choices, mode: "dropdown" } },
        },
        ...this._form.schema
          .slice(1)
          .filter(
            (field) =>
              ![
                "show_transfer_predictions",
                "show_destination_eta",
                "transfer_rows",
                "transfer_buffer",
              ].includes(field.name),
          ),
        ...(this._hass.states[this._config.entity]?.attributes?.journey_route
          ?.legs?.length > 0
          ? [{ name: "show_destination_eta", selector: { boolean: {} } }]
          : []),
        ...(this._hass.states[this._config.entity]?.attributes?.journey_route
          ?.legs?.length > 1
          ? [
              { name: "show_transfer_predictions", selector: { boolean: {} } },
              {
                name: "transfer_rows",
                selector: { number: { min: 1, max: 10, mode: "box" } },
              },
              {
                name: "transfer_buffer",
                selector: { number: { min: 1, max: 30, mode: "box" } },
              },
            ]
          : []),
      ];
      this._form.hass = this._hass;
      this._form.data = this._config;
    }
  }
  if (!customElements.get("wmata-station-card"))
    customElements.define("wmata-station-card", WmataStationCard);
  if (!customElements.get("wmata-station-card-editor"))
    customElements.define("wmata-station-card-editor", WmataStationCardEditor);
  window.customCards = window.customCards || [];
  if (!window.customCards.some((c) => c.type === "wmata-station-card"))
    window.customCards.push({
      type: "wmata-station-card",
      name: "WMATA Station Board",
      description:
        "Live Metrorail and Metrobus arrivals, with line and destination filters.",
      preview: true,
    });
  let plannerCount = 0;
  class WmataTripPlanner extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._listId = `wmata-stations-${++plannerCount}`;
    }
    setConfig(config) {
      if (!config?.entity?.startsWith("sensor."))
        throw new Error(
          "Choose a WMATA rail board or train map for API access.",
        );
      if (
        config.appearance !== undefined &&
        !validAppearance(config.appearance)
      )
        throw new Error("Choose a supported appearance preset.");
      if (
        config.transfer_buffer !== undefined &&
        (!Number.isInteger(config.transfer_buffer) ||
          config.transfer_buffer < 1 ||
          config.transfer_buffer > 30)
      )
        throw new Error("transfer_buffer must be an integer between 1 and 30.");
      for (const key of ["origin", "destination", "title"])
        if (config[key] !== undefined && typeof config[key] !== "string")
          throw new Error(`${key} must be a station name or text.`);
      if (this._config?.entity !== config.entity) {
        this._stations = null;
        this._catalogPending = false;
        this._catalogGeneration = (this._catalogGeneration || 0) + 1;
      }
      this._generation = (this._generation || 0) + 1;
      this._pending = null;
      this._query = null;
      this._config = { appearance: "native", transfer_buffer: 3, ...config };
      this.dataset.appearance = this._config.appearance;
      this.dataset.day = String(
        this._hass?.states?.["sun.sun"]?.state === "above_horizon",
      );
      this._build();
      this._loadStations();
    }
    set hass(hass) {
      const previous = this._hass;
      this._hass = hass;
      this.dataset.day = String(
        hass.states?.["sun.sun"]?.state === "above_horizon",
      );
      this._loadStations();
      if (
        this._result &&
        this._board &&
        (previous?.themes !== hass.themes ||
          previous?.states?.["sun.sun"] !== hass.states?.["sun.sun"])
      )
        this._showResult(this._result);
    }
    connectedCallback() {
      this._loadStations();
      if (!this._timer) this._timer = setInterval(() => this._refresh(), 30000);
    }
    disconnectedCallback() {
      clearInterval(this._timer);
      this._timer = null;
      this._generation = (this._generation || 0) + 1;
      this._catalogGeneration = (this._catalogGeneration || 0) + 1;
      this._pending = null;
      this._catalogPending = false;
    }
    getCardSize() {
      return 5 + (this._board?.getCardSize() || 0);
    }
    getGridOptions() {
      return { columns: 12, min_columns: 6 };
    }
    static getConfigElement() {
      return document.createElement("wmata-trip-planner-editor");
    }
    static getStubConfig(hass) {
      const entity = Object.keys(hass?.states || {}).find((id) => {
        const a = hass.states[id].attributes;
        return (
          (a.board_type === "station" && a.service_type === "train") ||
          (Array.isArray(a.trains) && Array.isArray(a.paths))
        );
      });
      return {
        type: "custom:wmata-trip-planner",
        entity: entity || "",
        appearance: "native",
      };
    }
    _build() {
      this.shadowRoot.innerHTML = `<style>${STYLE}
        :host{display:block;color:var(--primary-text-color,#202b35);font-family:var(--ha-font-family-body,Roboto,system-ui,sans-serif)}
        ha-card{display:block;border:var(--ha-card-border-width,1px) solid var(--divider-color,#ddd);border-radius:var(--ha-card-border-radius,24px);background:var(--ha-card-background,var(--card-background-color,#fff));box-shadow:var(--ha-card-box-shadow,none)}
        .planner-form{padding:16px}.planner-title{font-size:20px;font-weight:400;margin:0 0 12px}.fields{display:flex;gap:12px;flex-wrap:wrap}label{flex:1;min-width:150px;font-size:12px;line-height:1.8;color:var(--secondary-text-color,#64717b)}input{box-sizing:border-box;width:100%;font:inherit;font-size:14px;padding:11px 10px;border:1px solid var(--divider-color,#ccc);border-radius:8px;background:var(--secondary-background-color,#f4f6f7);color:var(--primary-text-color,#222)}
        .actions{display:flex;gap:8px;margin-top:12px}button{font:inherit;font-size:13px;border:1px solid var(--divider-color,#ccc);border-radius:9px;padding:9px 14px;background:transparent;color:inherit;cursor:pointer}button[type=submit]{background:var(--primary-color,#0076be);color:var(--text-primary-color,#fff);border-color:transparent}button:focus-visible,input:focus-visible{outline:2px solid var(--primary-color,#0076be);outline-offset:2px}.status,.scheduled{font-size:12px;line-height:1.6;margin-top:12px;color:var(--secondary-text-color,#64717b)}.result{margin-top:12px}.result:empty{display:none}
      </style>`;
      const card = element("ha-card");
      const form = element("form", "planner-form");
      form.append(
        element(
          "h2",
          "planner-title",
          this._config.title || "Metro trip planner",
        ),
      );
      const fields = element("div", "fields");
      for (const [key, label] of [
        ["origin", "From"],
        ["destination", "To"],
      ]) {
        const wrapper = element("label", null, label);
        const input = element("input");
        input.type = "text";
        input.setAttribute("aria-label", label + " station");
        input.setAttribute("list", this._listId);
        input.placeholder = "Search Metro stations";
        input.autocomplete = "off";
        input.value = this._config[key] || "";
        input.addEventListener("input", () => this._invalidate());
        this["_" + key + "Input"] = input;
        wrapper.append(input);
        fields.append(wrapper);
      }
      this._list = element("datalist");
      this._list.id = this._listId;
      const actions = element("div", "actions");
      const submit = element("button", null, "Plan trip");
      submit.type = "submit";
      const swap = element("button", null, "Swap stations");
      swap.type = "button";
      swap.onclick = () => {
        [this._originInput.value, this._destinationInput.value] = [
          this._destinationInput.value,
          this._originInput.value,
        ];
        this._invalidate();
        this._plan();
      };
      actions.append(submit, swap);
      this._status = element("div", "status", "Loading station names…");
      this._status.setAttribute("role", "status");
      this._scheduled = element("div", "scheduled");
      form.append(fields, this._list, actions, this._status, this._scheduled);
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        this._plan();
      });
      card.append(form);
      this._resultHost = element("div", "result");
      this._board = null;
      this._result = null;
      this.shadowRoot.append(card, this._resultHost);
      if (this._stations) this._fillStations();
    }
    _invalidate() {
      this._generation = (this._generation || 0) + 1;
      this._pending = null;
      this._query = null;
      this._result = null;
      this._board?.remove();
      this._board = null;
      this._scheduled.textContent = "";
      this._status.textContent = "Choose stations, then plan your trip.";
    }
    async _loadStations() {
      if (
        !this.isConnected ||
        !this._config ||
        !this._hass?.callWS ||
        this._catalogPending
      )
        return;
      if (this._stations) return;
      const generation = this._catalogGeneration;
      this._catalogPending = true;
      try {
        const result = await this._hass.callWS({
          type: "wmata/planner_stations",
          entity_id: this._config.entity,
        });
        if (!this.isConnected || generation !== this._catalogGeneration) return;
        if (!Array.isArray(result.stations)) throw new Error("Missing catalog");
        this._stations = result.stations;
        this._fillStations();
      } catch {
        if (this.isConnected && generation === this._catalogGeneration)
          this._status.textContent =
            "Station list unavailable. Check the selected WMATA rail board or map, then try Plan trip again.";
      } finally {
        if (generation === this._catalogGeneration)
          this._catalogPending = false;
      }
    }
    _fillStations() {
      this._list.replaceChildren();
      for (const station of this._stations) {
        const option = element("option");
        option.value = station.name;
        option.label = station.lines
          .map((line) => COLORS[line]?.[0] || line)
          .join(" / ");
        this._list.append(option);
      }
      this._status.textContent =
        "Choose stations, then plan your trip. Routes prefer fewer transfers, then fewer stops.";
    }
    _resolve(text) {
      const normalize = (value) =>
        value
          .toLocaleLowerCase()
          .normalize("NFKD")
          .replace(/[^a-z0-9]/g, "");
      const value = normalize(text);
      if (!value) return null;
      const exact = this._stations?.find(
        (s) => normalize(s.name) === value || normalize(s.code) === value,
      );
      const matches =
        this._stations?.filter((s) => normalize(s.name).includes(value)) || [];
      return exact || (matches.length === 1 ? matches[0] : null);
    }
    async _plan() {
      if (!this._stations) {
        await this._loadStations();
        if (!this._stations) return;
      }
      const from = this._resolve(this._originInput.value),
        to = this._resolve(this._destinationInput.value);
      if (!from || !to || from.code === to.code) {
        this._status.textContent =
          "Choose two different stations from the suggestions. Use a full station name if several match.";
        return;
      }
      this._originInput.value = from.name;
      this._destinationInput.value = to.name;
      this._query = { origin: from.code, destination: to.code };
      await this._refresh();
    }
    async _refresh() {
      if (
        !this.isConnected ||
        !this._query ||
        document.visibilityState === "hidden"
      )
        return;
      const key = JSON.stringify([this._config.entity, this._query]);
      if (this._pending === key) return;
      const generation = this._generation;
      this._pending = key;
      this._status.textContent = "Updating route and departures…";
      try {
        const result = await this._hass.callWS({
          type: "wmata/plan_trip",
          entity_id: this._config.entity,
          ...this._query,
        });
        if (!this.isConnected || generation !== this._generation) return;
        if (!result.route?.legs?.length || !Array.isArray(result.legs))
          throw new Error("Invalid route");
        this._result = result;
        this._showResult(result);
        this._status.textContent =
          "Live predictions refresh every 30 seconds while this card is open.";
      } catch {
        if (this.isConnected && generation === this._generation) {
          this._result = null;
          this._status.textContent =
            "Trip predictions unavailable. Retrying shortly.";
          if (this._board) {
            this._board._transferError = true;
            this._board._renderTransfers();
          }
        }
      } finally {
        if (generation === this._generation) this._pending = null;
      }
    }
    _showResult(result) {
      if (!this._board) {
        this._board = document.createElement("wmata-station-card");
        this._resultHost.append(this._board);
      }
      this._board.setJourneyPreview(this._hass, result, {
        appearance: this._config.appearance,
        transfer_buffer: this._config.transfer_buffer,
        max_rows: 8,
        show_filters: false,
      });
      const changes = result.route.legs.length - 1;
      this._scheduled.textContent = Number.isFinite(
        result.scheduled_ride_minutes,
      )
        ? `Baseline: about ${Math.ceil(result.scheduled_ride_minutes + changes * this._config.transfer_buffer)} min ${changes ? "riding and switching platforms" : "riding"}, plus train waits. The arrival estimate below includes train waits and labels timetable connections.`
        : "Scheduled ride times unavailable. Live departures are shown below when available.";
    }
  }
  class WmataTripPlannerEditor extends HTMLElement {
    setConfig(config) {
      this._config = { appearance: "native", transfer_buffer: 3, ...config };
      this._render();
    }
    set hass(hass) {
      this._hass = hass;
      this._render();
    }
    _render() {
      if (!this._config || !this._hass) return;
      if (!this._form) {
        this._form = document.createElement("ha-form");
        this._form.computeLabel = ({ name }) =>
          ({
            entity: "WMATA rail board or train map (API access)",
            appearance: "Appearance",
            origin: "Starting station (optional)",
            destination: "Destination station (optional)",
            transfer_buffer: "Minutes to change platforms",
            title: "Title",
          })[name] || name;
        this._form.addEventListener("value-changed", (event) => {
          event.stopPropagation();
          this._config = { ...this._config, ...event.detail.value };
          emit(this, "config-changed", { config: this._config });
        });
        this.append(this._form);
      }
      const options = Object.entries(this._hass.states || {})
        .filter(
          ([id, s]) =>
            id === this._config.entity ||
            (s.attributes.board_type === "station" &&
              s.attributes.service_type === "train") ||
            (Array.isArray(s.attributes.trains) &&
              Array.isArray(s.attributes.paths)),
        )
        .map(([value, s]) => ({
          value,
          label:
            s.attributes.friendly_name || s.attributes.station_name || value,
        }));
      this._form.schema = [
        {
          name: "entity",
          required: true,
          selector: { select: { options, mode: "dropdown" } },
        },
        {
          name: "appearance",
          selector: {
            select: { options: WMATA_APPEARANCES, mode: "dropdown" },
          },
        },
        { name: "origin", selector: { text: {} } },
        { name: "destination", selector: { text: {} } },
        {
          name: "transfer_buffer",
          selector: { number: { min: 1, max: 30, mode: "box" } },
        },
        { name: "title", selector: { text: {} } },
      ];
      this._form.hass = this._hass;
      this._form.data = this._config;
    }
  }
  if (!customElements.get("wmata-trip-planner"))
    customElements.define("wmata-trip-planner", WmataTripPlanner);
  if (!customElements.get("wmata-trip-planner-editor"))
    customElements.define("wmata-trip-planner-editor", WmataTripPlannerEditor);
  window.customCards.push({
    type: "wmata-trip-planner",
    name: "WMATA Trip Planner",
    description:
      "Search any two Metro stations for ride times, live trains and estimated connections.",
    preview: true,
  });
})();

if (!customElements.get("wmata-train-map")) {
  class WmataTrainMap extends HTMLElement {
    static getStubConfig(hass) {
      const entity = Object.keys(hass?.states || {}).find(
        (id) =>
          Array.isArray(hass.states[id].attributes?.trains) &&
          Array.isArray(hass.states[id].attributes?.paths),
      );
      return {
        type: "custom:wmata-train-map",
        entity: entity || "sensor.wmata_network_trains",
      };
    }
    getCardSize() {
      return 8;
    }
    static getConfigElement() {
      return document.createElement("wmata-map-editor");
    }
    setConfig(c) {
      this._disposeGeo();
      this.config = {
        height: 750,
        zoom: 1,
        view: "geographic",
        theme_mode: "auto",
        appearance: "standard",
        ...c,
      };
      if (!validAppearance(this.config.appearance))
        throw new Error("Choose a supported appearance preset.");
      if (!["geographic", "diagram"].includes(this.config.view))
        throw new Error("view must be geographic or diagram");
      if (!["auto", "dark", "light"].includes(this.config.theme_mode))
        throw new Error("theme_mode must be auto, dark or light");
      if (c.dark_mode !== undefined && typeof c.dark_mode !== "boolean")
        throw new Error("dark_mode must be true or false");
      if (
        !Number.isFinite(this.config.height) ||
        this.config.height < 250 ||
        this.config.height > 1600
      )
        throw new Error("height must be between 250 and 1600 pixels");
      if (
        !Number.isFinite(this.config.zoom) ||
        this.config.zoom < 1 ||
        this.config.zoom > 4
      )
        throw new Error("zoom must be between 1 and 4");
      this.dataset.appearance = this.config.appearance;
      this.view = this.config.view;
      this.zoom = this.config.zoom;
      this.last = null;
      if (this._hass) this.hass = this._hass;
    }
    _viewSelector() {
      const label = document.createElement("label");
      label.style.cssText =
        "display:flex;align-items:center;gap:10px;padding:8px 0";
      label.append(document.createTextNode("Map view"));
      const select = document.createElement("select");
      select.setAttribute("aria-label", "Map view");
      for (const [value, text] of [
        ["geographic", "OpenStreetMap"],
        ["diagram", "Official diagram"],
      ]) {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = text;
        select.append(option);
      }
      select.value = this.view || "geographic";
      select.onchange = () => {
        this.view = select.value;
        this.last = null;
        this._disposeGeo();
        this.hass = this._hass;
      };
      label.append(select);
      return label;
    }
    _disposeGeo() {
      clearInterval(this._stationTimer);
      this._stationTimer = null;
      this.querySelector("dialog")?.remove();
      if (this._map) {
        this._geoCenter = this._map.getCenter();
        this._geoZoom = this._map.getZoom();
        this._map.remove();
        this._map = null;
      }
      this._resizeObserver?.disconnect();
      this._geoContainer = null;
      this._geoGeneration = (this._geoGeneration || 0) + 1;
    }
    disconnectedCallback() {
      clearInterval(this._stationTimer);
      this.querySelector("dialog")?.remove();
      this._disposeGeo();
      this.last = null;
    }
    connectedCallback() {
      if (this._hass) {
        this.last = null;
        this.hass = this._hass;
      }
    }
    _styleFrame(card) {
      const preset = this.config.appearance;
      card.dataset.appearance = preset;
      if (preset === "native") {
        card.style.borderRadius = "var(--ha-card-border-radius,12px)";
        card.style.boxShadow = "var(--ha-card-box-shadow,none)";
        card.style.fontFamily =
          "var(--ha-font-family-body,Roboto,system-ui,sans-serif)";
      } else if (preset === "minimal") {
        card.style.border = "0";
        card.style.boxShadow = "none";
      } else if (preset === "mushroom") card.style.borderRadius = "28px";
      else if (preset === "glass") {
        card.style.background =
          "color-mix(in srgb,var(--card-background-color,#fff) 78%,transparent)";
        card.style.backdropFilter = "blur(20px)";
        card.style.borderRadius = "24px";
      } else if (["daylight", "orbit", "bento"].includes(preset))
        card.style.borderRadius = "24px";
    }
    async _renderGeographic(state) {
      if (!this.isConnected) return;
      if (this._map) {
        this._applyMapTheme();
        this._updateGeoTrains(state.attributes.trains || []);
        return;
      }
      if (this._geoContainer) return;
      const generation = this._geoGeneration || 0;
      const card = document.createElement("ha-card");
      card.style.cssText = "display:block;overflow:hidden;position:relative";
      this._styleFrame(card);
      const body = document.createElement("div");
      body.style.cssText = "padding:0;position:relative";
      const controls = document.createElement("div");
      controls.className = "wmata-map-controls";
      controls.style.cssText =
        "position:absolute;right:10px;top:10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;z-index:1000;padding:4px 8px;border-radius:6px;background:var(--wmata-map-surface,#fff);color:var(--wmata-map-text,#222);box-shadow:0 1px 5px #0003";
      controls.append(this._viewSelector());
      const full = document.createElement("button");
      full.textContent = "Full screen";
      const fit = document.createElement("button");
      fit.textContent = "Fit network";
      controls.append(fit, full);
      const map = document.createElement("div");
      map.style.cssText =
        "height:" +
        this.config.height +
        "px;min-height:250px;max-height:95vh;resize:vertical;overflow:hidden;isolation:isolate;background:#e6e9e8";
      map.className = "wmata-live-map";
      map.setAttribute("aria-label", "Live Metrorail trains on OpenStreetMap");
      full.onclick = () => map.requestFullscreen?.();
      const count = document.createElement("p");
      const warning = document.createElement("p");
      warning.setAttribute("role", "status");
      count.style.cssText =
        "position:absolute;left:10px;bottom:25px;z-index:900;margin:0;padding:3px 6px;font-size:11px;border-radius:4px;background:var(--wmata-map-surface,#fff);color:var(--wmata-map-text,#222)";
      warning.style.cssText =
        "position:absolute;left:10px;bottom:60px;z-index:900;background:var(--card-background-color,#fff);max-width:80%";
      body.append(controls, map, count, warning);
      card.append(body);
      this.replaceChildren(card);
      this._geoContainer = map;
      this._geoCount = count;
      warning.textContent = "Loading geographic map…";
      try {
        await this._loadLeaflet();
        const data = await this._routes();
        if (
          generation !== (this._geoGeneration || 0) ||
          this._geoContainer !== map ||
          !this.isConnected
        )
          return;
        const L = window.L;
        const leaflet = L.map(map, { scrollWheelZoom: true });
        this._map = leaflet;
        L.tileLayer(
          this.config.tile_url ||
            "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
          {
            maxZoom: 19,
            referrerPolicy: "strict-origin-when-cross-origin",
            attribution:
              this.config.tile_attribution ||
              '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          },
        )
          .on("tileerror", () => {
            warning.textContent =
              "Basemap tiles unavailable. Rail routes and train markers remain visible.";
          })
          .addTo(leaflet);
        this._applyMapTheme();
        const colors = {
          BL: "#0076be",
          RD: "#ba2630",
          YL: "#d3aa00",
          GR: "#008344",
          SV: "#687780",
          OR: "#db6500",
        };
        const bounds = [];
        for (const route of data.paths) {
          const coords = route.points.map(([lon, lat]) => [lat, lon]);
          bounds.push(...coords);
          L.polyline(coords, {
            color: colors[route.line] || "#555",
            weight: 4,
            opacity: 0.7,
            interactive: false,
          }).addTo(leaflet);
        }
        this._networkBounds = L.latLngBounds(bounds);
        leaflet.createPane("wmataStations").style.zIndex = "650";
        const stationTargets = [];
        for (const station of data.stations) {
          const label = document.createElement("span");
          label.textContent = station.name;
          const marker = L.circleMarker([station.point[1], station.point[0]], {
            pane: "wmataStations",
            radius: 6,
            color: "#36434f",
            weight: 1,
            fillColor: "#fff",
            fillOpacity: 1,
          })
            .bindTooltip(label)
            .on("click", () => this._stationPopup(station))
            .addTo(leaflet);
          stationTargets.push([marker, station]);
        }
        this._trainLayer = L.layerGroup().addTo(leaflet);
        fit.onclick = () =>
          leaflet.fitBounds(this._networkBounds, { padding: [24, 24] });
        if (this._geoCenter) leaflet.setView(this._geoCenter, this._geoZoom);
        else fit.onclick();
        for (const [marker, station] of stationTargets) {
          const target = marker.getElement();
          target?.setAttribute("tabindex", "0");
          target?.setAttribute("role", "button");
          target?.setAttribute("aria-label", station.name + " arrivals");
          if (target)
            target.onkeydown = (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                this._stationPopup(station);
              }
            };
        }
        this._resizeObserver = new ResizeObserver(() =>
          leaflet.invalidateSize({ pan: false }),
        );
        this._resizeObserver.observe(map);
        warning.textContent = "";
        this._updateGeoTrains(this.last?.attributes?.trains || []);
      } catch (error) {
        if (generation !== (this._geoGeneration || 0)) return;
        warning.textContent =
          "Geographic map could not load. Select Official diagram to view the system map.";
        this._map?.remove();
        this._map = null;
        this._resizeObserver?.disconnect();
        this._geoContainer = null;
      }
    }
    _refreshTime() {
      const timestamp = this.last?.attributes?.updated_at;
      const date = new Date(timestamp);
      return timestamp && Number.isFinite(date.getTime())
        ? "Last refreshed " +
            date.toLocaleTimeString([], {
              hour: "numeric",
              minute: "2-digit",
              second: "2-digit",
            })
        : "Refresh time unavailable";
    }
    _updateGeoTrains(trains) {
      const L = window.L;
      if (!this._trainLayer) return;
      this._trainLayer.clearLayers();
      const colors = {
        BL: "#0076be",
        RD: "#ba2630",
        YL: "#dfbe22",
        GR: "#008344",
        SV: "#687780",
        OR: "#db6500",
      };
      for (const train of trains.filter((t) => Array.isArray(t.geo_point))) {
        const badge = document.createElement("span");
        badge.textContent = colors[train.line] ? train.line : "?";
        badge.style.cssText =
          "display:flex;justify-content:center;align-items:center;width:26px;height:26px;box-sizing:border-box;border:2px solid white;border-radius:50%;background:" +
          (colors[train.line] || "#222") +
          ";color:" +
          (train.line === "YL" ? "black" : "white") +
          ";font:700 10px system-ui;box-shadow:0 1px 5px #0008";
        const marker = L.marker([train.geo_point[1], train.geo_point[0]], {
          icon: L.divIcon({
            html: badge,
            className: "wmata-geographic-train",
            iconSize: [26, 26],
            iconAnchor: [13, 13],
          }),
          title:
            "Train " +
            train.id +
            " · " +
            (train.destination || "Destination unavailable"),
          keyboard: true,
        });
        marker.on("click", () => this._popup(train));
        marker.addTo(this._trainLayer);
      }
      this._geoCount.textContent =
        trains.filter((t) => t.geo_point).length +
        " of " +
        trains.length +
        " trains mapped · " +
        this._refreshTime() +
        " · Estimated positions";
      this._geoCount.title = this.last?.attributes?.updated_at
        ? new Date(this.last.attributes.updated_at).toLocaleString()
        : "";
    }
    async _loadLeaflet() {
      const root = this.getRootNode();
      const cssHost = root === document ? document.head : root;
      if (!cssHost.querySelector("link[data-wmata-leaflet]")) {
        const css = document.createElement("link");
        css.rel = "stylesheet";
        css.href = "/wmata/vendor/leaflet.css";
        css.dataset.wmataLeaflet = "true";
        cssHost.append(css);
      }
      if (!cssHost.querySelector("style[data-wmata-map]")) {
        const style = document.createElement("style");
        style.dataset.wmataMap = "true";
        style.textContent =
          ".wmata-map-controls button,.wmata-map-controls select{padding:6px 8px;border:1px solid #8885;border-radius:4px;background:var(--wmata-map-surface,#fff);color:var(--wmata-map-text,#222)}.wmata-live-map[data-dark=true] .leaflet-control-zoom a{background:#202124;color:#eee;border-color:#555}";
        cssHost.append(style);
      }
      await import("/wmata/vendor/leaflet.js");
      return window.L;
    }
    async _routes() {
      if (!this._routeData) {
        const response = await fetch("/wmata/geo_routes.json");
        if (!response.ok) throw new Error("Rail route data unavailable");
        this._routeData = await response.json();
      }
      return this._routeData;
    }
    _isDark() {
      if (typeof this.config.dark_mode === "boolean")
        return this.config.dark_mode;
      return (
        this.config.theme_mode === "dark" ||
        (this.config.theme_mode === "auto" &&
          Boolean(this._hass?.themes?.darkMode))
      );
    }
    _applyMapTheme() {
      const dark = this._isDark();
      this.style.setProperty("--wmata-map-surface", dark ? "#202124" : "#fff");
      this.style.setProperty("--wmata-map-text", dark ? "#eee" : "#222");
      if (!this._map) return;
      // Match HA's raster-map treatment while leaving rail colors intact.
      this._map.getPane("tilePane").style.filter = dark
        ? "invert(0.9) hue-rotate(170deg) brightness(1.5) contrast(1.2) saturate(0.3)"
        : "none";
      const container = this._map.getContainer();
      container.dataset.dark = String(dark);
      container.style.background = dark ? "#1c1c1c" : "#e6e9e8";
    }
    _lineName(code) {
      return (
        {
          BL: "Blue",
          RD: "Red",
          GR: "Green",
          YL: "Yellow",
          SV: "Silver",
          OR: "Orange",
        }[code] ||
        code ||
        "Unreported"
      );
    }
    _dialog(title) {
      clearInterval(this._stationTimer);
      this.querySelector("dialog")?.remove();
      const dialog = document.createElement("dialog");
      const dark = this._isDark();
      dialog.style.cssText =
        "max-width:620px;width:88vw;max-height:85vh;overflow:auto;border:1px solid var(--divider-color);border-radius:16px;padding:24px;background:" +
        (dark ? "#202124" : "#fff") +
        ";color:" +
        (dark ? "#eee" : "#222");
      const heading = document.createElement("h2");
      heading.textContent = title;
      dialog.append(heading);
      const content = document.createElement("div");
      dialog.append(content);
      const close = document.createElement("button");
      close.textContent = "Close";
      close.onclick = () => dialog.close();
      dialog.append(close);
      dialog.addEventListener("close", () => {
        if (!this.contains(dialog)) return;
        clearInterval(this._stationTimer);
        this._stationTimer = null;
        dialog.remove();
        if (this.view === "diagram" && this._hass) {
          this.last = null;
          this.hass = this._hass;
        }
      });
      this.append(dialog);
      dialog.showModal();
      return content;
    }
    _stationPopup(station) {
      const content = this._dialog(station.name + " arrivals");
      const refresh = async () => {
        if (!content.isConnected) return;
        if (!content.childNodes.length)
          content.textContent = "Loading arrivals…";
        try {
          const result = await this._hass.callWS({
            type: "wmata/station_arrivals",
            entity_id: this.config.entity || "sensor.wmata_network_trains",
            station_code: station.code,
          });
          if (!content.isConnected) return;
          content.replaceChildren();
          if (!result.arrivals.length) {
            content.textContent = "No upcoming trains are currently predicted.";
            return;
          }
          for (const train of result.arrivals) {
            const row = document.createElement("div");
            row.style.cssText =
              "display:grid;grid-template-columns:65px minmax(0,1fr) auto;gap:10px;padding:12px 0;border-bottom:1px solid #8884";
            const line = document.createElement("strong");
            line.textContent = this._lineName(train.line);
            const destination = document.createElement("span");
            destination.textContent =
              (train.destination || "Destination unavailable") +
              (train.last_train ? " · Last train" : "") +
              " · " +
              (train.direction || "Direction unavailable");
            const due = document.createElement("span");
            due.textContent =
              train.status === "boarding"
                ? "Boarding"
                : train.status === "arriving"
                  ? "Arriving"
                  : train.minutes == null
                    ? "No estimate"
                    : train.minutes + " min";
            row.append(line, destination, due);
            content.append(row);
          }
          const updated = document.createElement("p");
          updated.style.fontSize = "12px";
          updated.textContent =
            "Updated " +
            new Date(result.updated_at || Date.now()).toLocaleTimeString();
          content.append(updated);
        } catch (error) {
          if (content.isConnected)
            content.textContent =
              error.message || "Arrivals unavailable. Retrying shortly.";
        }
      };
      refresh();
      this._stationTimer = setInterval(refresh, 30000);
    }
    _popup(train) {
      const content = this._dialog("Train " + train.id);
      for (const [label, value] of [
        ["Line", this._lineName(train.line)],
        ["Destination", train.destination || "Unknown"],
        ["Service", train.service],
        [
          "Track serves",
          (train.track_lines || [])
            .map((code) => this._lineName(code))
            .join(", "),
        ],
        ["Circuit", train.circuit],
        [
          "Position",
          train.position_type === "nearby"
            ? "Near a connected route circuit"
            : (this.view === "geographic" ? train.geo_point : train.point)
              ? "On mapped route"
              : "Unavailable",
        ],
      ]) {
        const row = document.createElement("p");
        row.textContent = label + " · " + (value ?? "Unknown");
        content.append(row);
      }
    }

    set hass(h) {
      this._hass = h;
      const state =
        h.states[this.config?.entity || "sensor.wmata_network_trains"];
      const themeChanged = this._lastDark !== this._isDark();
      this._lastDark = this._isDark();
      if (state && state === this.last && !themeChanged) return;
      this.last = state;
      if (this.view === "diagram" && this.querySelector("dialog[open]")) return;
      if (
        (this.view || "geographic") === "geographic" &&
        state &&
        state.state !== "unavailable" &&
        state.attributes.paths
      ) {
        this._renderGeographic(state);
        return;
      }
      this._disposeGeo();
      const card = document.createElement("ha-card");
      this._styleFrame(card);
      card.header = "Metrorail train map";
      const body = document.createElement("div");
      body.style.padding = "0 16px 16px";
      card.append(body);
      this.replaceChildren(card);
      body.append(this._viewSelector());
      if (!state || state.state === "unavailable" || !state.attributes.paths) {
        body.textContent = "Train positions unavailable";
        return;
      }
      const { paths, trains } = state.attributes;
      const colors = {
        BL: "#0076be",
        RD: "#ba2630",
        YL: "#e3be29",
        GR: "#008344",
        SV: "#929aa0",
        OR: "#db6500",
      };
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      const coords = paths.flatMap((r) => r.points);
      if (!coords.length) {
        body.textContent = "Route geometry unavailable";
        return;
      }
      const xy = (p) => p;
      svg.setAttribute("viewBox", "0 240 988 830");
      svg.style.cssText =
        "display:block;max-width:none;width:" +
        (this.zoom || 1) * 100 +
        "%;height:auto";
      const viewport = document.createElement("div");
      viewport.style.cssText =
        "height:" +
        this.config.height +
        "px;min-height:250px;max-height:95vh;resize:vertical;overflow:auto;border:1px solid var(--divider-color,#ddd)";
      const controls = document.createElement("div");
      controls.style.cssText =
        "display:flex;gap:12px;align-items:center;margin:8px 0";
      const label = document.createElement("label");
      label.textContent = "Map zoom";
      const zoom = document.createElement("input");
      zoom.type = "range";
      zoom.min = "1";
      zoom.max = "4";
      zoom.step = "0.1";
      zoom.value = this.zoom || 1;
      zoom.setAttribute("aria-label", "Map zoom");
      zoom.oninput = () => {
        this.zoom = Number(zoom.value);
        svg.style.width = this.zoom * 100 + "%";
      };
      const expand = document.createElement("button");
      expand.textContent = "Full screen";
      expand.onclick = () => viewport.requestFullscreen?.();
      controls.append(label, zoom, expand);
      body.append(controls);

      const background = document.createElementNS(svg.namespaceURI, "image");
      background.setAttribute("href", "/wmata/system-map.png");
      background.setAttribute("width", "988");
      background.setAttribute("height", "1200");
      background.style.filter = this._isDark()
        ? "invert(0.9) hue-rotate(170deg) brightness(1.2)"
        : "none";
      svg.append(background);
      function shape(tag, attrs) {
        const n = document.createElementNS(svg.namespaceURI, tag);
        for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
        svg.append(n);
        return n;
      }
      const stationLayer = document.createElementNS(svg.namespaceURI, "g");
      svg.append(stationLayer);
      this._routes()
        .then((data) => {
          if (!stationLayer.isConnected) return;
          for (const station of data.stations.filter(
            (st) => st.diagram_point,
          )) {
            const target = document.createElementNS(svg.namespaceURI, "circle");
            target.setAttribute("cx", station.diagram_point[0]);
            target.setAttribute("cy", station.diagram_point[1]);
            target.setAttribute("r", 8);
            target.setAttribute("fill", "transparent");
            target.setAttribute("tabindex", "0");
            target.setAttribute("role", "button");
            target.setAttribute("aria-label", station.name + " arrivals");
            target.onclick = () => this._stationPopup(station);
            target.onkeydown = (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                this._stationPopup(station);
              }
            };
            stationLayer.append(target);
          }
        })
        .catch(() => {});
      const info = document.createElement("p");
      for (const t of trains.filter((t) => t.point)) {
        const [cx, cy] = xy(t.point);
        const dot = shape("circle", {
          cx,
          cy,
          r: 7,
          fill: colors[t.line] || "#222",
          stroke: t.position_type === "nearby" ? "black" : "white",
          "stroke-width": 1,
        });
        const label =
          "Train " +
          t.id +
          " · " +
          (t.line ||
            "Line unreported · Track serves " +
              ((t.track_lines || []).join("/") || "unknown")) +
          " · Circuit " +
          (t.circuit ?? "unknown") +
          " · Destination " +
          (t.destination || "unknown") +
          (t.position_type === "nearby"
            ? " · Near connected route circuit"
            : "");
        const title = document.createElementNS(svg.namespaceURI, "title");
        title.textContent = label;
        dot.append(title);
        const code = shape("text", {
          x: cx,
          y: cy + 0.4,
          "text-anchor": "middle",
          "dominant-baseline": "middle",
          "font-size": 7,
          "font-weight": 800,
          fill: t.line === "YL" ? "black" : "white",
          "pointer-events": "none",
        });
        code.textContent = colors[t.line] ? t.line : "?";
        dot.setAttribute("tabindex", "0");
        dot.setAttribute("role", "button");
        dot.setAttribute("aria-label", label);
        dot.onclick = () => this._popup(t);
        dot.onkeydown = (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            this._popup(t);
          }
        };
      }
      info.textContent =
        trains.filter((t) => t.point).length +
        " of " +
        trains.length +
        " trains mapped · " +
        this._refreshTime() +
        " · Estimated positions";
      info.title = state.attributes.updated_at
        ? new Date(state.attributes.updated_at).toLocaleString()
        : "";
      viewport.append(svg);
      body.append(viewport, info);
    }
  }
  customElements.define("wmata-train-map", WmataTrainMap);
  window.customCards.push({
    type: "wmata-train-map",
    name: "WMATA train map",
    description: "Live network train positions",
  });
}

if (!customElements.get("wmata-map-editor")) {
  class WmataMapEditor extends HTMLElement {
    setConfig(c) {
      this.config = {
        height: 750,
        zoom: 1,
        view: "geographic",
        theme_mode: "auto",
        appearance: "standard",
        ...c,
      };
      if (!validAppearance(this.config.appearance))
        throw new Error("Choose a supported appearance preset.");
      if (!["geographic", "diagram"].includes(this.config.view))
        throw new Error("view must be geographic or diagram");
      if (!["auto", "dark", "light"].includes(this.config.theme_mode))
        throw new Error("theme_mode must be auto, dark or light");
      if (c.dark_mode !== undefined && typeof c.dark_mode !== "boolean")
        throw new Error("dark_mode must be true or false");
      this.render();
    }
    set hass(h) {
      this._hass = h;
      this.render();
    }
    render() {
      if (!this.config || !this._hass) return;
      if (!this.form) {
        this.form = document.createElement("ha-form");
        this.form.computeLabel = ({ name }) =>
          ({
            entity: "Train map sensor",
            height: "Map height (pixels)",
            zoom: "Diagram zoom",
            view: "Default map view",
            theme_mode: "Map theme",
            tile_url: "Tile URL (optional)",
            tile_attribution: "Tile attribution (optional)",
          })[name] || name;
        this.form.addEventListener("value-changed", (e) => {
          e.stopPropagation();
          this.config = { ...this.config, ...e.detail.value };
          this.dispatchEvent(
            new CustomEvent("config-changed", {
              detail: { config: this.config },
              bubbles: true,
              composed: true,
            }),
          );
        });
        this.append(this.form);
      }
      this.form.computeLabel = ({ name }) =>
        ({
          appearance: "Appearance",
          view: "Map view",
          theme_mode: "Map brightness",
          entity: "Train map",
          height: "Height",
          zoom: "Diagram zoom",
          tile_url: "Custom tile URL",
          tile_attribution: "Custom attribution",
        })[name] || name;
      this.form.schema = [
        {
          name: "entity",
          selector: {
            select: {
              options: Object.entries(this._hass.states)
                .filter(
                  ([id, s]) =>
                    Array.isArray(s.attributes.trains) &&
                    Array.isArray(s.attributes.paths),
                )
                .map(([value, s]) => ({
                  value,
                  label: s.attributes.friendly_name || value,
                })),
              mode: "dropdown",
            },
          },
        },
        {
          name: "view",
          selector: {
            select: {
              options: [
                { value: "geographic", label: "OpenStreetMap" },
                { value: "diagram", label: "Official diagram" },
              ],
              mode: "dropdown",
            },
          },
        },
        {
          name: "appearance",
          selector: {
            select: { options: WMATA_APPEARANCES, mode: "dropdown" },
          },
        },
        {
          name: "theme_mode",
          selector: {
            select: { options: ["auto", "dark", "light"], mode: "dropdown" },
          },
        },
        {
          name: "height",
          selector: { number: { min: 250, max: 1600, mode: "box" } },
        },
        {
          name: "zoom",
          selector: { number: { min: 1, max: 4, step: 0.1, mode: "slider" } },
        },
        { name: "tile_url", selector: { text: {} } },
        { name: "tile_attribution", selector: { text: {} } },
      ];
      this.form.hass = this._hass;
      this.form.data = this.config;
    }
  }
  customElements.define("wmata-map-editor", WmataMapEditor);
}
