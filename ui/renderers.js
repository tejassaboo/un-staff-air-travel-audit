// The audit's verdict drawn as a travel-unit approval slip: the entitled cabin, a stamp that reads
// COMPLIANT or NOT COMPLIANT, and each violation code as a line item. It uses only the kit.
import { h, humanize, statusPill } from "./kit/components.js";

const RULES = {
  CABIN_ABOVE_ENTITLEMENT: "C7: proposed cabin above the entitlement",
  ROUTE_EXCEEDS_TIME_LIMIT: "C6: route is 240 min or more slower than the most direct",
  ROUTE_NOT_LEAST_COSTLY: "C6: a cheaper route passes the time rule",
  LATE_ARRANGEMENT: "C8: arrangements finalized fewer than 16 days ahead",
  LATE_REQUEST_ABOVE_ECONOMY: "C9: business proposed, request fewer than 21 days ahead",
};

function slip(audit) {
  const lines = audit.violations.length
    ? audit.violations.map((code) => h("li", {}, h("code", { text: code }), h("span", { class: "rule", text: RULES[code] ?? "" })))
    : [h("li", { class: "clear", text: "No violations" })];
  return h(
    "div",
    { class: "slip" },
    h(
      "div",
      { class: "head" },
      h("span", { class: "title", text: "Travel audit slip" }),
      statusPill(audit.compliant ? "COMPLIANT" : "NOT COMPLIANT", audit.compliant ? "ok" : "bad", { icon: true }),
    ),
    h("div", { class: "cabin" }, h("span", { class: "label", text: "Entitled cabin" }), h("strong", { text: humanize(audit.entitled_cabin) })),
    h("ol", { class: "lines" }, lines),
  );
}

export default { UnAuditOutput: slip };
