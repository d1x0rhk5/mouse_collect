(function () {
  const origin = window.location.origin;
  const routes = {
    shoppingHome: origin + "/shopping/",
    shoppingAccount: origin + "/shopping/customer/account/",
    shoppingLogin: origin + "/shopping/customer/account/login/",
    shoppingRegister: origin + "/shopping/customer/account/create/",
    shoppingForgotPassword: origin + "/shopping/customer/account/forgotpassword/",
    shoppingWishlist: origin + "/shopping/wishlist/",
    shoppingCart: origin + "/shopping/checkout/cart/",
    shoppingAdvancedSearch: origin + "/shopping/catalogsearch/advanced/",
    shoppingSearchResults: origin + "/shopping/catalogsearch/result/",
    redditHome: origin + "/reddit/",
    redditComments: origin + "/reddit/comments/",
    redditLogin: origin + "/reddit/login/",
    redditRegistration: origin + "/reddit/registration/",
    redditResetPassword: origin + "/reddit/reset_password/",
    redditForums: origin + "/reddit/forums/",
    redditWiki: origin + "/reddit/wiki/",
    redditFeaturedHot: origin + "/reddit/featured/hot/",
    redditAllNew: origin + "/reddit/all/new/",
    redditAllActive: origin + "/reddit/all/active/",
    redditAllTop: origin + "/reddit/all/top/",
    redditAllControversial: origin + "/reddit/all/controversial/",
    redditAllMostCommented: origin + "/reddit/all/most_commented/",
    redditCommunity: origin + "/reddit/r/webarena/",
    redditThread: origin + "/reddit/r/webarena/comments/static-frontend-check/"
  };

  const exactRoutes = new Map([
    ["http://localhost:9999/all/hot", routes.redditHome],
    ["http://localhost:9999/comments", routes.redditComments],
    ["http://localhost:9999/login", routes.redditLogin],
    ["http://localhost:9999/registration", routes.redditRegistration],
    ["http://localhost:9999/reset_password", routes.redditResetPassword],
    ["http://localhost:9999/forums", routes.redditForums],
    ["http://localhost:9999/wiki", routes.redditWiki],
    ["http://localhost:9999/featured/hot", routes.redditFeaturedHot],
    ["http://localhost:9999/all/new", routes.redditAllNew],
    ["http://localhost:9999/all/active", routes.redditAllActive],
    ["http://localhost:9999/all/top?t=day", routes.redditAllTop],
    ["http://localhost:9999/all/controversial?t=day", routes.redditAllControversial],
    ["http://localhost:9999/all/most_commented?t=day", routes.redditAllMostCommented],
    ["http://localhost:9999/f/memes", routes.redditCommunity],
    ["http://localhost:9999/f/memes/41616/which-of-the-following-fruits-will-be-the-2nd-most-popular", routes.redditThread]
  ]);

  function normalizeReferenceUrl(url) {
    const path = url.pathname.replace(/\/+$/, "") || "/";
    const query = url.search || "";
    return url.protocol + "//" + url.host + path + query;
  }

  function isReferenceHost(url) {
    return url.host === "localhost:7770" || url.host === "localhost:9999";
  }

  function fallbackRoute(url) {
    if (url.host === "localhost:7770") {
      return routes.shoppingHome;
    }
    if (url.host === "localhost:9999") {
      return routes.redditHome;
    }
    return null;
  }

  function shouldIgnoreNavigation(value) {
    if (!value) {
      return true;
    }

    return (
      value.startsWith("#") ||
      value.startsWith("javascript:") ||
      value.startsWith("mailto:") ||
      value.startsWith("tel:")
    );
  }

  function mapShopping(url) {
    const path = url.pathname || "/";

    if (path === "/") {
      return routes.shoppingHome;
    }
    if (path.startsWith("/customer/account/login")) {
      return routes.shoppingLogin;
    }
    if (path.startsWith("/customer/account/create")) {
      return routes.shoppingRegister;
    }
    if (path.startsWith("/customer/account/forgotpassword")) {
      return routes.shoppingForgotPassword;
    }
    if (path.startsWith("/customer/account")) {
      return routes.shoppingAccount;
    }
    if (path.startsWith("/wishlist/index/")) {
      return routes.shoppingWishlist;
    }
    if (path.startsWith("/wishlist")) {
      return routes.shoppingWishlist;
    }
    if (path.startsWith("/catalogsearch/advanced/result")) {
      return routes.shoppingSearchResults;
    }
    if (path.startsWith("/catalogsearch/advanced")) {
      return routes.shoppingAdvancedSearch;
    }
    if (path.startsWith("/catalogsearch/result")) {
      return routes.shoppingSearchResults;
    }
    if (
      path.startsWith("/checkout/cart/add") ||
      path.startsWith("/checkout/") ||
      url.search.includes("options=cart")
    ) {
      return routes.shoppingCart;
    }
    if (path.startsWith("/newsletter/subscriber")) {
      return routes.shoppingHome;
    }

    return origin + "/shopping" + path;
  }

  function mapReddit(url) {
    const path = url.pathname.replace(/\/+$/, "") || "/";

    if (path === "/" || path.startsWith("/all/hot")) {
      return routes.redditHome;
    }
    if (path.startsWith("/login")) {
      return routes.redditLogin;
    }
    if (path.startsWith("/registration")) {
      return routes.redditRegistration;
    }
    if (path.startsWith("/reset_password")) {
      return routes.redditResetPassword;
    }
    if (path.startsWith("/forums")) {
      return routes.redditForums;
    }
    if (path.startsWith("/wiki")) {
      return routes.redditWiki;
    }
    if (path === "/comments") {
      return routes.redditComments;
    }
    if (path.startsWith("/featured/hot")) {
      return routes.redditFeaturedHot;
    }
    if (path.startsWith("/all/new")) {
      return routes.redditAllNew;
    }
    if (path.startsWith("/all/active")) {
      return routes.redditAllActive;
    }
    if (path.startsWith("/all/top")) {
      return routes.redditAllTop;
    }
    if (path.startsWith("/all/controversial")) {
      return routes.redditAllControversial;
    }
    if (path.startsWith("/all/most_commented")) {
      return routes.redditAllMostCommented;
    }
    if (/^\/f\/[^/]+\/\d+\//.test(path)) {
      return routes.redditThread;
    }
    if (path.startsWith("/f/")) {
      return routes.redditCommunity;
    }

    return routes.redditHome;
  }

  function localPostRedirect(form, resolved) {
    const method = (form.getAttribute("method") || "GET").toUpperCase();
    if (method !== "POST") {
      return null;
    }

    const path = resolved.pathname.replace(/\/+$/, "") || "/";

    if (path === "/reddit/login") {
      return routes.redditHome;
    }
    if (path === "/reddit/registration") {
      return routes.redditLogin;
    }
    if (path === "/reddit/reset_password") {
      return routes.redditLogin;
    }
    if (path === "/shopping/customer/account/login") {
      return routes.shoppingAccount;
    }
    if (path === "/shopping/customer/account/create") {
      return routes.shoppingAccount;
    }
    if (path === "/shopping/customer/account/forgotpassword") {
      return routes.shoppingLogin;
    }
    if (path.startsWith("/shopping/checkout/cart/add")) {
      return routes.shoppingCart;
    }
    if (path.startsWith("/shopping/wishlist/index/add")) {
      return routes.shoppingWishlist;
    }
    if (path === "/shopping") {
      return routes.shoppingHome;
    }
    if (path === "/reddit") {
      return window.location.href;
    }

    return null;
  }

  function getReferenceBase() {
    const meta = document.querySelector('meta[name="reference-base"]');
    return meta ? meta.content : document.baseURI;
  }

  function resolveUrl(value, base) {
    try {
      return new URL(value, base);
    } catch (error) {
      return null;
    }
  }

  function resolveDocumentUrl(value) {
    return resolveUrl(value, document.baseURI);
  }

  function resolveReferenceUrl(value) {
    return resolveUrl(value, getReferenceBase());
  }

  function toMirrorUrl(value) {
    if (shouldIgnoreNavigation(value)) {
      return null;
    }

    const localResolved = resolveDocumentUrl(value);
    if (localResolved && localResolved.origin === origin) {
      return null;
    }

    const resolved = resolveReferenceUrl(value);
    if (!resolved || resolved.origin === origin) {
      return null;
    }

    const exactRoute = exactRoutes.get(normalizeReferenceUrl(resolved));
    if (exactRoute) {
      return exactRoute;
    }

    if (resolved.host === "localhost:7770") {
      return mapShopping(resolved);
    }
    if (resolved.host === "localhost:9999") {
      return mapReddit(resolved);
    }

    return null;
  }

  function rewriteAnchors() {
    document.querySelectorAll("a[href]").forEach(function (anchor) {
      const href = anchor.getAttribute("href");
      if (shouldIgnoreNavigation(href)) {
        return;
      }

      const resolved = resolveDocumentUrl(href) || resolveReferenceUrl(href);
      if (!resolved || resolved.origin === origin) {
        return;
      }

      const mirrorUrl = toMirrorUrl(href);
      if (mirrorUrl) {
        anchor.setAttribute("href", mirrorUrl);
      } else if (isReferenceHost(resolved)) {
        anchor.setAttribute("href", fallbackRoute(resolved));
      }
    });
  }

  function rewriteForms() {
    document.querySelectorAll("form").forEach(function (form) {
      const action = form.getAttribute("action") || window.location.href;
      if (shouldIgnoreNavigation(action)) {
        return;
      }

      const mirrorUrl = toMirrorUrl(action);
      if (mirrorUrl) {
        form.setAttribute("action", mirrorUrl);
      }
    });
  }

  function setDropdownExpanded(dropdown, expanded) {
    if (!(dropdown instanceof Element)) {
      return;
    }

    dropdown.classList.toggle("dropdown--expanded", expanded);
    const toggle = dropdown.querySelector(".dropdown__toggle");
    if (toggle instanceof HTMLElement) {
      toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
    }
  }

  function closeDropdowns(except) {
    document.querySelectorAll(".dropdown.dropdown--expanded").forEach(function (dropdown) {
      if (dropdown !== except) {
        setDropdownExpanded(dropdown, false);
      }
    });
  }

  function initDropdowns() {
    document.querySelectorAll(".dropdown > .dropdown__toggle").forEach(function (toggle) {
      toggle.setAttribute("aria-expanded", "false");
      if (!toggle.hasAttribute("aria-haspopup")) {
        toggle.setAttribute("aria-haspopup", "true");
      }
    });

    document.addEventListener(
      "click",
      function (event) {
        const toggle = event.target.closest(".dropdown > .dropdown__toggle");
        if (toggle) {
          const dropdown = toggle.parentElement;
          const expanded = dropdown.classList.contains("dropdown--expanded");
          event.preventDefault();
          closeDropdowns(dropdown);
          setDropdownExpanded(dropdown, !expanded);
          return;
        }

        if (!event.target.closest(".dropdown")) {
          closeDropdowns(null);
        }
      },
      true
    );

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeDropdowns(null);
      }
    });
  }

  document.addEventListener(
    "click",
    function (event) {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }

      const anchor = event.target.closest("a[href]");
      if (!anchor) {
        return;
      }

      if (anchor.target && anchor.target !== "_self") {
        return;
      }

      const href = anchor.getAttribute("href");
      if (shouldIgnoreNavigation(href)) {
        return;
      }

      const mirrorUrl = toMirrorUrl(href);
      if (mirrorUrl) {
        event.preventDefault();
        event.stopImmediatePropagation();
        window.location.assign(mirrorUrl);
        return;
      }

      const resolved = resolveDocumentUrl(href) || resolveReferenceUrl(href);
      if (!resolved || resolved.origin === origin) {
        return;
      }

      if (isReferenceHost(resolved)) {
        event.preventDefault();
        event.stopImmediatePropagation();
        window.location.assign(fallbackRoute(resolved));
      }
    },
    true
  );

  document.addEventListener(
    "submit",
    function (event) {
      const form = event.target;
      if (!(form instanceof HTMLFormElement)) {
        return;
      }

      const action = form.getAttribute("action") || window.location.href;
      if (shouldIgnoreNavigation(action)) {
        return;
      }

      const resolved = resolveDocumentUrl(action) || resolveReferenceUrl(action);
      if (!resolved) {
        return;
      }

      if (resolved.origin === origin) {
        const localRedirect = localPostRedirect(form, resolved);
        if (localRedirect) {
          event.preventDefault();
          event.stopImmediatePropagation();
          window.location.assign(localRedirect);
        }
        return;
      }

      const mirrorUrl = toMirrorUrl(action);
      if (mirrorUrl) {
        event.preventDefault();
        event.stopImmediatePropagation();
        window.location.assign(mirrorUrl);
        return;
      }

      if (isReferenceHost(resolved)) {
        event.preventDefault();
        event.stopImmediatePropagation();
        window.location.assign(fallbackRoute(resolved));
      }
    },
    true
  );

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      rewriteAnchors();
      rewriteForms();
      initDropdowns();
    });
  } else {
    rewriteAnchors();
    rewriteForms();
    initDropdowns();
  }
})();
