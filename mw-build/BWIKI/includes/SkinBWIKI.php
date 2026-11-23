<?php

namespace MediaWiki\Skins\BWIKI;

use MediaWiki\MediaWikiServices;
use MediaWiki\Revision\RevisionRecord;
use MediaWiki\Skin\SkinMustache;
use Throwable;

/**
 * BWIKI skin for MediaWiki 1.46.
 *
 * The template reproduces the public BWIKI page shell with local MediaWiki
 * data. It does not load any CSS, JavaScript, widget or API from biligame.com.
 */
class SkinBWIKI extends SkinMustache {
	/**
	 * @inheritDoc
	 */
	public function getTemplateData(): array {
		$data = parent::getTemplateData();
		$sidebar = $data['data-portlets-sidebar'] ?? [];
		$portlets = [];

		if ( isset( $sidebar['data-portlets-first'] ) && is_array( $sidebar['data-portlets-first'] ) ) {
			$portlets[] = $sidebar['data-portlets-first'];
		}
		foreach ( $sidebar['array-portlets-rest'] ?? [] as $portlet ) {
			if ( is_array( $portlet ) ) {
				$portlets[] = $portlet;
			}
		}

		$data['html-bwiki-desktop-menus'] = $this->buildDesktopMenus( $portlets );
		$data['html-bwiki-mobile-menus'] = $this->buildMobileMenus( $portlets );

		/* Core flattens sidebar lines deeper than two asterisks
		 * (Skin::addToSidebarPlain only knows headings and items), so a
		 * MediaWiki:Sidebar that uses "***" loses its third level. When the
		 * sidebar is nested, parse the raw message ourselves and render the
		 * real tree for both the desktop bar and the mobile drawer. */
		$nested = $this->buildSidebarTree( $portlets );
		if ( $nested !== null ) {
			$data['html-bwiki-desktop-menus'] = $this->renderDesktopTree( $nested );
			$data['html-bwiki-mobile-menus'] = $this->renderMobileTree( $nested );
		}

		$data['html-bwiki-mobile-sns'] = $this->buildMobileSns();
		$data['html-bwiki-personal-items'] = $this->buildPersonalItems( $data );
		$data['html-bwiki-user-status'] = $this->buildUserStatus();
		$data['html-bwiki-action-items'] = $this->buildActionItems( $data );

		$revisionData = $this->getRevisionData();
		$data['bwiki-last-editor'] = $revisionData['editor'];
		$data['bwiki-last-modified'] = $revisionData['modified'];
		$data['html-bwiki-contributors'] = $this->buildContributors( $revisionData );

		$data['bwiki-logo-src'] = $this->getNativeLogoSrc();
		$data['bwiki-mainpage-href'] = $data['link-mainpage'] ?? './';
		$data['bwiki-current-year'] = date( 'Y' );
		$data['bwiki-notifications-href'] = \MediaWiki\SpecialPage\SpecialPage::getTitleFor( 'Notifications' )->getLocalURL();

		return $data;
	}

	/**
	 * Site logo from the native $wgLogos configuration (LocalSettings.php).
	 * The BWIKI header logo is a wide wordmark, so prefer the native
	 * 'wordmark' entry, then svg/1x/1.5x/2x; falls back to the bundled
	 * skin logo when nothing is configured.
	 */
	private function getNativeLogoSrc(): string {
		$logos = $this->getConfig()->get( \MediaWiki\MainConfigNames::Logos ) ?? [];
		if ( is_array( $logos ) ) {
			if ( !empty( $logos['wordmark']['src'] ) ) {
				return (string)$logos['wordmark']['src'];
			}
			foreach ( [ 'svg', '1x', '1.5x', '2x' ] as $key ) {
				if ( !empty( $logos[$key] ) && is_string( $logos[$key] ) ) {
					return $logos[$key];
				}
			}
			$icon = $logos['icon'] ?? null;
			if ( is_string( $icon ) && $icon !== '' ) {
				return $icon;
			}
			if ( is_array( $icon ) && !empty( $icon['src'] ) ) {
				return (string)$icon['src'];
			}
		}
		$stylePath = rtrim( (string)( $GLOBALS['wgStylePath'] ?? '/skins' ), '/' );
		return $stylePath . '/BWIKI/resources/logo.svg';
	}

	/**
	 * Render MediaWiki sidebar portlets using BWIKI desktop wrapper classes.
	 *
	 * @param array $portlets
	 */
	private function buildDesktopMenus( array $portlets ): string {
		$html = '<div class="menu-wrap wiki-menu-ul-1  clearfix">';
		foreach ( $portlets as $portlet ) {
			$label = $this->escape( (string)( $portlet['label'] ?? '' ) );
			$items = $this->extractMenuItems( (string)( $portlet['html-items'] ?? '' ) );
			$html .= '<div class="wiki-menu-li-1">';
			$html .= '<a href="javascript:;" class="menu-title">' . $label;
			if ( $items ) {
				$html .= ' <span class="caret"></span>';
			}
			$html .= '</a><div class="wiki-menu-ul-2 ">';
			foreach ( $items as $item ) {
				$html .= '<div class="wiki-menu-li-2">' . $this->renderMenuLink( $item ) . '</div>';
			}
			$html .= '</div></div>';
		}
		$html .= '</div>';
		return $html;
	}

	/**
	 * Parse MediaWiki:Sidebar into a nested tree when it uses at least three
	 * asterisk levels. Pseudo sections (SEARCH / TOOLBOX / LANGUAGES) are
	 * filled from the core-generated portlet data, everything else resolves
	 * its links the same way Skin::createSidebarItem does.
	 *
	 * @param array $portlets Core sidebar portlets (first + rest)
	 * @return array|null null when the sidebar has no nesting
	 */
	private function buildSidebarTree( array $portlets ): ?array {
		$raw = $this->msg( 'sidebar' )->inContentLanguage()->plain();
		if ( trim( $raw ) === '' || !preg_match( '/^\*\*\*[^\n*]/m', $raw ) ) {
			return null;
		}

		$sections = [];
		$current = null;
		foreach ( explode( "\n", $raw ) as $line ) {
			$line = rtrim( $line, "\r" );
			if ( !str_starts_with( $line, '*' ) ) {
				continue;
			}
			$level = strspn( $line, '*' );
			$rest = trim( substr( $line, $level ), ' ' );
			if ( $level === 1 ) {
				$sections[] = [ 'heading' => $rest, 'items' => [] ];
				$current = count( $sections ) - 1;
				continue;
			}
			if ( $current === null ) {
				continue;
			}
			$item = $this->resolveSidebarItem( $rest );
			if ( $item === null ) {
				continue;
			}
			$container = &$this->sidebarLevel( $sections[$current]['items'], $level - 2 );
			$container[] = $item;
			unset( $container );
		}

		return $this->mergeSidebarPortlets( $sections, $portlets );
	}

	/**
	 * Walk (and create when needed) the child-item list at the given depth.
	 *
	 * @param array &$items Sibling items at the current level
	 * @param int $depth Levels to descend (0 = here)
	 * @return array Reference to the item list at the target depth
	 */
	private function &sidebarLevel( array &$items, int $depth ): array {
		if ( $depth <= 0 || count( $items ) === 0 ) {
			return $items;
		}
		$last = count( $items ) - 1;
		if ( !isset( $items[$last]['children'] ) || !is_array( $items[$last]['children'] ) ) {
			$items[$last]['children'] = [];
		}
		return $this->sidebarLevel( $items[$last]['children'], $depth - 1 );
	}

	/**
	 * Resolve one "target|text" sidebar line into a link record.
	 *
	 * @param string $line
	 * @return array|null null when the line must be skipped
	 */
	private function resolveSidebarItem( string $line ): ?array {
		if ( !str_contains( $line, '|' ) ) {
			return null;
		}
		[ $target, $text ] = array_map( 'trim', explode( '|', $line, 2 ) );
		if ( $target === '' ) {
			return null;
		}

		$msgText = $this->msg( $text );
		$label = $msgText->exists() ? $msgText->text() : $text;

		$msgLink = $this->msg( $target )->inContentLanguage();
		$link = $msgLink->exists() ? $msgLink->text() : $target;
		if ( $link === '-' ) {
			return null;
		}

		$item = [
			'href' => '',
			'text' => $label,
			'title' => '',
			'target' => '',
			'rel' => '',
			'children' => [],
		];

		$protocols = (array)( $GLOBALS['wgUrlProtocols'] ?? [] );
		if ( $protocols && preg_match( '/^(?:' . implode( '|', $protocols ) . ')/', $link ) ) {
			$item['href'] = $link;
			if ( !empty( $GLOBALS['wgNoFollowLinks'] ) ) {
				$item['rel'] = 'nofollow';
			}
			if ( !empty( $GLOBALS['wgExternalLinkTarget'] ) ) {
				$item['target'] = (string)$GLOBALS['wgExternalLinkTarget'];
			}
		} else {
			$title = MediaWikiServices::getInstance()->getTitleFactory()->newFromText( $link );
			$item['href'] = $title ? $title->fixSpecialName()->getLinkURL() : '';
		}

		return $item;
	}

	/**
	 * Replace pseudo headings with the matching core portlet and resolve the
	 * label message for the real headings.
	 *
	 * @param array $sections Parsed sidebar sections
	 * @param array $portlets Core sidebar portlets
	 */
	private function mergeSidebarPortlets( array $sections, array $portlets ): array {
		$pool = [];
		foreach ( $portlets as $portlet ) {
			$items = [];
			foreach ( $this->extractMenuItems( (string)( $portlet['html-items'] ?? '' ) ) as $item ) {
				$item['children'] = [];
				$items[] = $item;
			}
			$pool[] = [ 'label' => (string)( $portlet['label'] ?? '' ), 'items' => $items ];
		}

		$out = [];
		foreach ( $sections as $section ) {
			$heading = strtoupper( $section['heading'] );
			if ( $heading === 'SEARCH' || $heading === 'TOOLBOX' || $heading === 'LANGUAGES' ) {
				if ( $heading === 'SEARCH' ) {
					$want = $this->msg( 'search' )->text();
				} elseif ( $heading === 'TOOLBOX' ) {
					$want = $this->msg( 'toolbox' )->text();
				} else {
					$want = $this->msg( 'otherlanguages' )->text();
				}
				foreach ( $pool as $i => $portlet ) {
					if ( $portlet['label'] === $want ) {
						$out[] = [ 'label' => $want, 'items' => $portlet['items'] ];
						unset( $pool[$i] );
						$pool = array_values( $pool );
						break;
					}
				}
				continue;
			}
			$msg = $this->msg( $section['heading'] );
			$out[] = [
				'label' => $msg->exists() ? $msg->text() : $section['heading'],
				'items' => $section['items'],
			];
		}
		return $out;
	}

	/**
	 * Render the nested tree as the desktop bar (BWIKI wiki-menu classes).
	 *
	 * @param array $sections
	 */
	private function renderDesktopTree( array $sections ): string {
		$html = '<div class="menu-wrap wiki-menu-ul-1  clearfix">';
		foreach ( $sections as $section ) {
			$items = is_array( $section['items'] ?? null ) ? $section['items'] : [];
			$html .= '<div class="wiki-menu-li-1">';
			$html .= '<a href="javascript:;" class="menu-title">' . $this->escape( (string)$section['label'] );
			if ( $items ) {
				$html .= ' <span class="caret"></span>';
			}
			$html .= '</a><div class="wiki-menu-ul-2 ">';
			if ( $items ) {
				$html .= $this->renderDesktopItems( $items, 2 );
			}
			$html .= '</div></div>';
		}
		return $html . '</div>';
	}

	/**
	 * Render one level of desktop items. Level 2 sits directly inside the
	 * .wiki-menu-ul-2 panel emitted by renderDesktopTree(), deeper levels
	 * bring their own .wiki-menu-ul-N container.
	 *
	 * @param array $items
	 * @param int $level
	 */
	private function renderDesktopItems( array $items, int $level ): string {
		$html = $level > 2 ? '<div class="wiki-menu-ul-' . $level . '">' : '';
		foreach ( $items as $item ) {
			$children = is_array( $item['children'] ?? null ) ? $item['children'] : [];
			$html .= '<div class="wiki-menu-li-' . $level . '">';
			$html .= $this->renderTreeLink( $item, $children, $level >= 3 ? 'menu-title-1' : 'menu-title' );
			if ( $children ) {
				$html .= $this->renderDesktopItems( $children, $level + 1 );
			}
			$html .= '</div>';
		}
		return $level > 2 ? $html . '</div>' : $html;
	}

	/**
	 * Render the nested tree for the mobile drawer (ul-menu classes).
	 *
	 * @param array $sections
	 */
	private function renderMobileTree( array $sections ): string {
		$html = '<ul class="ul-menu-1">';
		foreach ( $sections as $section ) {
			$items = is_array( $section['items'] ?? null ) ? $section['items'] : [];
			$html .= '<li class="li-menu-1">';
			$html .= '<a href="javascript:;" class="menu-title">' . $this->escape( (string)$section['label'] );
			if ( $items ) {
				$html .= ' <span class="caret nav-rotate"></span>';
			}
			$html .= '</a>';
			if ( $items ) {
				$html .= $this->renderMobileItems( $items, 2 );
			}
			$html .= '</li>';
		}
		return $html . '</ul>';
	}

	/**
	 * @param array $items
	 * @param int $level
	 */
	private function renderMobileItems( array $items, int $level ): string {
		$html = '<ul class="ul-menu-' . $level . ' clearfix">';
		foreach ( $items as $item ) {
			$children = is_array( $item['children'] ?? null ) ? $item['children'] : [];
			$html .= '<li class="li-menu-' . $level . '">';
			$html .= $this->renderTreeLink( $item, $children, $level >= 3 ? 'menu-title-1' : 'menu-title' );
			if ( $children ) {
				$html .= $this->renderMobileItems( $children, $level + 1 );
			}
			$html .= '</li>';
		}
		return $html . '</ul>';
	}

	/**
	 * One <a> for the tree renderers. Parents get an inert target and a
	 * caret, matching the reference markup.
	 *
	 * @param array $item
	 * @param array $children
	 * @param string $class
	 */
	private function renderTreeLink( array $item, array $children, string $class ): string {
		$href = $children ? 'javascript:;' : (string)$item['href'];
		$attributes = ' href="' . $this->escape( $href ) . '" class="' . $class . '"';
		foreach ( [ 'title', 'target', 'rel' ] as $name ) {
			$value = (string)( $item[$name] ?? '' );
			if ( $value !== '' ) {
				$attributes .= ' ' . $name . '="' . $this->escape( $value ) . '"';
			}
		}
		$html = '<a' . $attributes . '>' . $this->escape( (string)$item['text'] );
		if ( $children ) {
			$html .= '<span class="caret nav-rotate"></span>';
		}
		return $html . '</a>';
	}

	/**
	 * Footer link grid inside the mobile drawer (.mobile-sns-wrap).
	 */
	private function buildMobileSns(): string {
		$factory = MediaWikiServices::getInstance()->getTitleFactory();
		$mainHref = $factory->newMainPage()->getLocalURL();
		$links = [
			[ $mainHref, 'BWIKI首页' ],
			[ $factory->newFromText( 'Special:RecentChanges' )->getLocalURL(), '最近更改' ],
			[ $factory->newFromText( 'Special:SpecialPages' )->getLocalURL(), '特殊页面' ],
			[ 'https://www.mediawiki.org/wiki/Special:MyLanguage/Help:Contents', 'MediaWiki帮助' ],
		];
		/* Login state lives in the right-hand header slot on desktop, but
		 * that slot is hidden on phones — put it into the drawer grid. */
		if ( $this->getUser()->isRegistered() ) {
			$links[] = [ \MediaWiki\SpecialPage\SpecialPage::getTitleFor( 'Userlogout' )->getLocalURL(), $this->msg( 'logout' )->text() ];
		} else {
			$links[] = [ \MediaWiki\SpecialPage\SpecialPage::getTitleFor( 'Userlogin' )->getLocalURL(), $this->msg( 'login' )->text() ];
		}
		$html = '<div class="mobile-sns-wrap">';
		foreach ( $links as [ $href, $label ] ) {
			$html .= '<a href="' . $this->escape( $href ) . '" class="mobile-sns-item">' . $this->escape( $label ) . '</a>';
		}
		$html .= '</div>';
		return $html;
	}

	/**
	 * Render the same sidebar portlets using BWIKI mobile wrapper classes.
	 *
	 * @param array $portlets
	 */
	private function buildMobileMenus( array $portlets ): string {
		$html = '<ul class="ul-menu-1">';
		foreach ( $portlets as $portlet ) {
			$label = $this->escape( (string)( $portlet['label'] ?? '' ) );
			$items = $this->extractMenuItems( (string)( $portlet['html-items'] ?? '' ) );
			$html .= '<li class="li-menu-1">';
			if ( $items ) {
				$html .= '<i class="mobile-right"></i>';
			}
			$html .= '<a href="javascript:;" class="menu-title">' . $label;
			if ( $items ) {
				$html .= ' <span class="caret nav-rotate"></span>';
			}
			$html .= '</a>';
			if ( $items ) {
				$html .= '<ul class="ul-menu-2 clearfix">';
				foreach ( $items as $item ) {
					$html .= '<li class="li-menu-2">' . $this->renderMenuLink( $item ) . '</li>';
				}
				$html .= '</ul>';
			}
			$html .= '</li>';
		}
		$html .= '</ul>';
		return $html;
	}

	/**
	 * Convert the core portlet list markup into simple link records.
	 */
	private function extractMenuItems( string $html ): array {
		if ( trim( $html ) === '' || !class_exists( '\\DOMDocument' ) ) {
			return [];
		}

		$document = new \DOMDocument();
		$previous = libxml_use_internal_errors( true );
		$loaded = $document->loadHTML(
			'<?xml encoding="UTF-8"><ul id="bwiki-portlet-items">' . $html . '</ul>',
			LIBXML_HTML_NOIMPLIED | LIBXML_HTML_NODEFDTD
		);
		libxml_clear_errors();
		libxml_use_internal_errors( $previous );
		if ( !$loaded ) {
			return [];
		}

		$root = $document->getElementById( 'bwiki-portlet-items' );
		if ( !$root ) {
			return [];
		}

		$items = [];
		foreach ( $root->childNodes as $node ) {
			if ( !( $node instanceof \DOMElement ) || strtolower( $node->tagName ) !== 'li' ) {
				continue;
			}
			$link = null;
			foreach ( $node->getElementsByTagName( 'a' ) as $candidate ) {
				$link = $candidate;
				break;
			}
			if ( !$link ) {
				continue;
			}
			$items[] = [
				'href' => $link->getAttribute( 'href' ),
				'text' => trim( $link->textContent ),
				'title' => $link->getAttribute( 'title' ),
				'target' => $link->getAttribute( 'target' ),
				'rel' => $link->getAttribute( 'rel' ),
			];
		}
		return $items;
	}

	/**
	 * @param array $item
	 */
	private function renderMenuLink( array $item ): string {
		$attributes = ' href="' . $this->escape( (string)$item['href'] ) . '" class="menu-title"';
		foreach ( [ 'title', 'target', 'rel' ] as $name ) {
			$value = (string)( $item[$name] ?? '' );
			if ( $value !== '' ) {
				$attributes .= ' ' . $name . '="' . $this->escape( $value ) . '"';
			}
		}
		return '<a' . $attributes . '>' . $this->escape( (string)$item['text'] ) . '</a>';
	}

	private function buildPersonalItems( array $data ): string {
		$html = '';
		foreach ( [ 'data-user-page', 'data-user-interface-preferences', 'data-notifications', 'data-user-menu' ] as $key ) {
			$html .= (string)( $data['data-portlets'][$key]['html-items'] ?? '' );
		}
		return $html;
	}

	/**
	 * Right-hand header slot. The reference site shows "我的消息 / 关于本站"
	 * there; this skin renders the native MediaWiki login state instead:
	 * avatar + username + logout when logged in, login / create account
	 * otherwise. Links are the native special pages with a returnto.
	 */
	private function buildUserStatus(): string {
		$user = $this->getUser();
		$title = $this->getTitle();
		$returnto = $title ? [ 'returnto' => $title->getPrefixedText() ] : [];
		$html = '<div class="bwiki-user-status">';
		if ( $user->isRegistered() ) {
			$name = $user->getName();
			// Prefer the SocialProfile avatar when that extension is active,
			// otherwise fall back to the first-letter badge.
			$avatarInner = null;
			if ( class_exists( 'wAvatar' ) && ( $GLOBALS['wgUserProfileDisplay']['avatar'] ?? true ) !== false ) {
				try {
					$avatar = new \wAvatar( $user->getId(), 'm' );
					$avatarUrl = $avatar->getAvatarURL( [ 'raw' => true ] );
					if ( $avatarUrl ) {
						$avatarInner = '<img class="bwiki-avatar-img" src="'
							. $this->escape( $avatarUrl ) . '" alt="'
							. $this->escape( $name ) . '" width="28" height="28">';
					}
				} catch ( \Throwable $e ) {
					$avatarInner = null;
				}
			}
			if ( $avatarInner === null ) {
				$avatarInner = '<span class="bwiki-avatar">'
					. $this->escape( mb_substr( $name, 0, 1 ) ) . '</span>';
			}
			$html .= '<span class="bwiki-user-avatar">' . $avatarInner . '</span>'
				. '<a class="bwiki-user-name" href="'
				. $this->escape( $user->getUserPage()->getLocalURL() )
				. '">' . $this->escape( $name ) . '</a>'
				. '<a class="bwiki-user-logout" href="'
				. $this->escape( \MediaWiki\SpecialPage\SpecialPage::getTitleFor( 'Userlogout' )->getLocalURL( $returnto ) )
				. '">' . $this->escape( $this->msg( 'logout' )->text() ) . '</a>';
		} else {
			$html .= '<a class="bwiki-user-login" href="'
				. $this->escape( \MediaWiki\SpecialPage\SpecialPage::getTitleFor( 'Userlogin' )->getLocalURL( $returnto ) )
				. '">' . $this->escape( $this->msg( 'login' )->text() ) . '</a>'
				. '<span class="bwiki-user-sep">/</span>'
				. '<a class="bwiki-user-create" href="'
				. $this->escape( \MediaWiki\SpecialPage\SpecialPage::getTitleFor( 'CreateAccount' )->getLocalURL( $returnto ) )
				. '">' . $this->escape( $this->msg( 'createaccount' )->text() ) . '</a>';
		}
		return $html . '</div>';
	}

	private function buildActionItems( array $data ): string {
		$html = '';
		foreach ( [ 'data-associated-pages', 'data-views', 'data-actions', 'data-variants' ] as $key ) {
			$html .= (string)( $data['data-portlets'][$key]['html-items'] ?? '' );
		}
		return $html;
	}

	private function getRevisionData(): array {
		$result = [
			'editor' => $this->msg( 'bwiki-system-user' )->text(),
			'editor-id' => 0,
			'modified' => '',
			'contributions-url' => '',
		];

		try {
			$revisionId = $this->getTitle()->getLatestRevID();
			if ( !$revisionId ) {
				return $result;
			}
			$services = MediaWikiServices::getInstance();
			$revision = $services->getRevisionLookup()->getRevisionById( $revisionId );
			if ( !$revision ) {
				return $result;
			}
			$user = $revision->getUser( RevisionRecord::RAW );
			if ( $user ) {
				$result['editor'] = $user->getName();
				$result['editor-id'] = $user->getId();
				$result['contributions-url'] = $services->getSpecialPageFactory()
					->getTitleForAlias( 'Contributions/' . $user->getName() )
					->getLocalURL();
			}
			$timestamp = $revision->getTimestamp();
			if ( $timestamp ) {
				$result['modified'] = $this->getLanguage()->userDate( $timestamp, $this->getUser() );
			}
		} catch ( Throwable ) {
			// Keep the skin usable when a page has no readable revision metadata.
		}
		return $result;
	}

	private function buildContributors( array $revisionData ): string {
		$editor = $this->escape( (string)$revisionData['editor'] );
		$url = $this->escape( (string)$revisionData['contributions-url'] );
		if ( $url === '' ) {
			$url = '#';
		}
		$initial = $editor !== '' ? mb_substr( $editor, 0, 1 ) : '?';
		$inner = $this->getAvatarInner( $revisionData, $initial );
		return '<div class="wiki-componment-rank" id="biliContributors">'
			. '<input id="bili_contributor_num" type="hidden" value="1">'
			. '<a class="rank-title" href="' . $url . '">' . $this->escape( $this->msg( 'bwiki-page-contributors' )->text() ) . ' :</a>'
			. '<div class="rank-top3"><div class="rank-item-wrap"><div class="rank-item">'
			. '<a href="' . $url . '" class="image-wrap"><div class="bwiki-avatar">' . $inner . '</div></a>'
			. '<div class="rank-item-detail-wrap"><div class="rank-item-detail">'
			. '<div class="detail-pic"><div class="bwiki-avatar">' . $inner . '</div></div>'
			. '<div class="detail-des"><div class="des-name">' . $editor . '</div><div class="des-content"></div></div>'
			. '<div class="detail-follow detail-follow-normal">' . $this->escape( $this->msg( 'bwiki-contributor-label' )->text() ) . '</div>'
			. '</div></div></div></div></div></div>';
	}

	/**
	 * Inner markup for a circular editor badge: the SocialProfile avatar
	 * image when that extension is active, otherwise the first letter.
	 */
	private function getAvatarInner( array $revisionData, string $initial ): string {
		try {
			if ( class_exists( 'wAvatar' )
				&& ( $GLOBALS['wgUserProfileDisplay']['avatar'] ?? true ) !== false
				&& !empty( $revisionData['editor-id'] )
			) {
				$avatar = new \wAvatar( (int)$revisionData['editor-id'], 'm' );
				$avatarUrl = $avatar->getAvatarURL( [ 'raw' => true ] );
				if ( $avatarUrl ) {
					return '<img class="bwiki-avatar-img" src="'
						. $this->escape( $avatarUrl ) . '" alt="'
						. $initial . '" width="30" height="30">';
				}
			}
		} catch ( \Throwable $e ) {
			// Fall back to the letter badge below.
		}
		return $this->escape( $initial );
	}

	private function escape( string $value ): string {
		return htmlspecialchars( $value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8' );
	}
}
