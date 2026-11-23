/* BWIKI skin interactions. No remote script or site-level Common.js is used. */
(function () {
	'use strict';

	function onActivate(element, callback) {
		if (!element) {
			return;
		}
		element.addEventListener('click', callback);
		element.addEventListener('keydown', function (event) {
			if (event.key === 'Enter' || event.key === ' ') {
				event.preventDefault();
				callback(event);
			}
		});
	}

	function followPortletLink(selector) {
		var link = document.querySelector(selector);
		if (link && link.href) {
			window.location.href = link.href;
		}
	}

	/* Desktop dropdown menus. Level 1 opens on hover (tune.css) and every
	 * level toggles on click/tap; clicking elsewhere closes them all. */
	function initDesktopMenus() {
		function submenuOf(item) {
			for (var i = 0; i < item.children.length; i++) {
				var child = item.children[i];
				if (/wiki-menu-ul-\d/.test(child.className || '')) {
					return child;
				}
			}
			return null;
		}

		document.addEventListener('click', function (event) {
			var title = event.target.closest('.menu-wrap .menu-title');
			if (title) {
				var item = title.parentElement;
				if (!item || !/(^| )wiki-menu-li-\d/.test(item.className || '')) {
					return;
				}
				var submenu = submenuOf(item);
				if (submenu && submenu.querySelector('a')) {
					event.preventDefault();
					var wasOpen = item.classList.contains('menu-open');
					Array.prototype.forEach.call(item.parentElement.children, function (sibling) {
						sibling.classList.remove('menu-open');
					});
					if (!wasOpen) {
						item.classList.add('menu-open');
					}
				}
				return;
			}
			/* Click anywhere else closes open dropdowns. */
			document.querySelectorAll('.menu-wrap .menu-open').forEach(function (open) {
				open.classList.remove('menu-open');
			});
		});
	}

	/* Mobile drawer navigation. The panel is parked off screen by tune.css
	 * (transform), which slides it in when .mobile-nav-open is present. */
	function initMobileNavigation() {
		var button = document.getElementById('navBar');
		var menu = document.getElementById('bwikiDrawer') || document.querySelector('.mobile-nav-menu');
		var mask = document.getElementById('mobileMask');
		if (!menu) {
			return;
		}
		var closeButton = menu.querySelector('.bwiki-drawer-close');
		var title = menu.querySelector('.bwiki-drawer-title');

		function setSubLabel(open, label) {
			menu.classList.toggle('bwiki-sub-open', open);
			if (title) {
				title.textContent = open ? (label || '') : '';
			}
		}

		function closeSubmenus() {
			menu.querySelectorAll('.li-menu-1.submenu-open, .sub-open').forEach(function (item) {
				item.classList.remove('submenu-open', 'sub-open');
			});
			setSubLabel(false);
		}

		function setOpen(open) {
			menu.classList.toggle('mobile-nav-open', open);
			menu.setAttribute('aria-hidden', open ? 'false' : 'true');
			if (button) {
				button.classList.toggle('collapsed', !open);
				button.setAttribute('aria-expanded', open ? 'true' : 'false');
			}
			if (mask) {
				mask.classList.toggle('mobile-mask-open', open);
			}
			document.body.classList.toggle('bwiki-drawer-open', open);
			if (!open) {
				closeSubmenus();
			}
		}

		onActivate(button, function () {
			setOpen(!menu.classList.contains('mobile-nav-open'));
		});
		onActivate(mask, function () {
			setOpen(false);
		});
		onActivate(closeButton, function () {
			setOpen(false);
		});

		/* Tap a section title to slide its submenu over the drawer
		 * (.li-menu-1) or expand deeper levels inline (.li-menu-2+);
		 * the header back arrow closes an open submenu, or the drawer
		 * itself when no submenu is showing (reference behaviour). */
		document.addEventListener('click', function (event) {
			if (!menu.classList.contains('mobile-nav-open')) {
				return;
			}
			var back = event.target.closest('.mobile-nav-menu .back-icon');
			if (back) {
				event.preventDefault();
				if (menu.querySelectorAll('.li-menu-1.submenu-open').length) {
					closeSubmenus();
				} else {
					setOpen(false);
				}
				return;
			}
			var row = event.target.closest('.mobile-nav-menu li');
			if (row) {
				/* The bundle's .li-menu-1:before row overlay makes the <li>
				 * itself the touch target, so resolve the row (not the link). */
				var submenu = null;
				for (var i = 0; i < row.children.length; i++) {
					var child = row.children[i];
					if (/ul-menu-\d/.test(child.className || '')) {
						submenu = child;
						break;
					}
				}
				var ownLink = row.querySelector(':scope > a');
				var tappedLink = event.target.closest('.mobile-nav-menu li a');
				if (submenu && submenu.querySelector('a') && (!tappedLink || tappedLink === ownLink)) {
					event.preventDefault();
					var isTop = row.classList.contains('li-menu-1');
					var cls = isTop ? 'submenu-open' : 'sub-open';
					var wasOpen = row.classList.contains(cls);
					Array.prototype.forEach.call(row.parentElement.children, function (sibling) {
						sibling.classList.remove(cls);
					});
					if (!wasOpen) {
						row.classList.add(cls);
						if (isTop) {
							setSubLabel(true, ownLink ? ownLink.textContent.trim() : '');
						}
					} else if (isTop) {
						setSubLabel(false);
					}
					return;
				}
			}
			var plain = event.target.closest('.mobile-nav-menu a[href]');
			if (plain && plain.getAttribute('href') !== 'javascript:;') {
				setOpen(false);
			}
		});

		document.addEventListener('keydown', function (event) {
			if (event.key === 'Escape') {
				setOpen(false);
			}
		});
	}

	function initSearch() {
		var input = document.getElementById('searchInput');
		var toggle = document.getElementById('navSearch');
		var formBox = document.querySelector('.form-box');
		var mobileBox = null;

		/* Clear button works for the original and the cloned celling search. */
		document.addEventListener('click', function (event) {
			var clear = event.target.closest('.search-close');
			if (clear) {
				var box = clear.closest('form');
				var field = box && box.querySelector('.mw-searchInput, #searchInput');
				if (field) {
					field.value = '';
					field.focus();
				}
			}
		});

		onActivate(toggle, function () {
			if (!formBox) {
				return;
			}
			if (!mobileBox) {
				mobileBox = formBox.cloneNode(true);
				mobileBox.classList.add('mobile-search-open');
				var header = document.querySelector('.wiki-header');
				header.appendChild(mobileBox);
				if (mobileBox.querySelector('#searchInput')) {
					mobileBox.querySelector('#searchInput').focus();
				}
			} else {
				mobileBox.remove();
				mobileBox = null;
			}
		});
	}

	function initPageTools() {
		onActivate(document.querySelector('.reset'), function () {
			window.location.reload();
		});
		onActivate(document.querySelector('.history'), function () {
			followPortletLink('#ca-history a');
		});
		onActivate(document.querySelector('.remarkWiki'), function () {
			followPortletLink('#ca-edit a, #ca-ve-edit a, #ca-viewsource a');
		});

		var actions = document.getElementById('p-cactions');
		var heading = document.getElementById('p-cactions-label');
		onActivate(heading, function () {
			if (actions) {
				actions.classList.toggle('menu-open');
			}
		});
	}

	function initToc() {
		var button = document.getElementById('tocBtn');
		onActivate(button, function () {
			var toc = document.getElementById('toc');
			if (toc) {
				toc.classList.toggle('bwiki-toc-open');
			}
		});
	}

	/* Fixed navigation bar (the "celling" nav). Once the in-page nav scrolls
	 * out of view, a clone appears docked to the top of the viewport. */
	function initCellingNav() {
		var nav = document.getElementById('navbar');
		if (!nav) {
			return;
		}

		var celling = document.createElement('div');
		celling.className = 'bwiki-celling hidden-xs hidden-sm';
		var clone = nav.cloneNode(true);
		clone.removeAttribute('id');
		celling.appendChild(clone);
		document.body.appendChild(celling);

		var threshold = 0;
		function measure() {
			var rect = nav.getBoundingClientRect();
			threshold = rect.bottom + (window.pageYOffset || document.documentElement.scrollTop);
		}

		function update() {
			if (window.innerWidth < 992) {
				celling.classList.remove('bwiki-celling-show');
				return;
			}
			var offset = window.pageYOffset || document.documentElement.scrollTop;
			celling.classList.toggle('bwiki-celling-show', offset > threshold);
		}

		window.addEventListener('resize', function () {
			measure();
			update();
		});
		window.addEventListener('scroll', update, { passive: true });
		measure();
		update();
	}

	function init() {
		initDesktopMenus();
		initMobileNavigation();
		initSearch();
		initPageTools();
		initToc();
		initCellingNav();
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();
