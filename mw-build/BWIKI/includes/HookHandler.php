<?php

namespace MediaWiki\Skins\BWIKI;

use MediaWiki\MediaWikiServices;

/**
 * Adds the heavy pre-built bundle stylesheets as static <link> tags.
 *
 * The free host intermittently truncates large load.php responses, which
 * left pages unstyled. Serving these files directly lets the web server
 * (not PHP) deliver them reliably. Bump $version when files change.
 *
 * Also mounts two per-skin customisation pages, injected only for this
 * skin and after tune.css so they win the cascade:
 *   MediaWiki:BWIKI.css  – extra CSS (inline <style>, last in <head>)
 *   MediaWiki:BWIKI.js   – extra JS (runs after jquery/mediawiki.util)
 * Both live in the MediaWiki namespace, i.e. only users with
 * `editinterface` can change them.
 */
class HookHandler {

	private const BUNDLE_VERSION = '22';

	private const BUNDLE_FILES = [
		'bootstrap.min.css',
		'rank-buddle.css',
		'vector.css',
		'styles.css',
		'toapp-buddle.css',
		'pluginsCommon-buddle.css',
	];

	/**
	 * @param \OutputPage $out
	 * @param \Skin $skin
	 */
	public function onBeforePageDisplay( $out, $skin ): void {
		if ( $skin->getSkinName() !== 'bwiki' ) {
			return;
		}
		$base = rtrim( (string)( $GLOBALS['wgStylePath'] ?? '/skins' ), '/' ) . '/BWIKI/resources';
		foreach ( self::BUNDLE_FILES as $file ) {
			$out->addStyle( $base . '/bundle/' . $file . '?v=' . self::BUNDLE_VERSION );
		}
		// Skin CSS + alignment layer must stay last in the cascade.
		$out->addStyle( $base . '/skin.css?v=' . self::BUNDLE_VERSION );
		$out->addStyle( $base . '/tune.css?v=' . self::BUNDLE_VERSION );

		// Site-level, skin-scoped customisation (after everything above).
		$css = $this->readCustomPage( 'BWIKI.css' );
		if ( $css !== null ) {
			// Inline <style> lands after the <link> tags, so these rules win
			// against skin.css / tune.css at equal specificity.
			$out->addInlineStyle( $css );
		}
		$js = $this->readCustomPage( 'BWIKI.js' );
		if ( $js !== null ) {
			// The page may use jQuery ($) and mw.* helpers. The ResourceLoader
			// startup script is asynchronous, so `mw` can still be undefined
			// when this inline tag runs — poll briefly instead of assuming it
			// exists (DOMContentLoaded is not enough: mw may land later).
			$script = '(function(){var tries=0;function run(){'
				. 'if(window.mw&&mw.loader&&mw.loader.using){'
				. 'mw.loader.using(["mediawiki.util","jquery"]).then(function(){'
				. "\n" . $js . "\n"
				. '});'
				. '}else if(++tries<200){setTimeout(run,50);}'
				. '}'
				. 'if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",run);}else{run();}'
				. '})();';
			$out->addInlineScript( $script );
		}
	}

	/**
	 * Raw text of MediaWiki:<name>, or null when the page is missing or blank.
	 *
	 * @param string $name
	 * @return string|null
	 */
	private function readCustomPage( string $name ): ?string {
		static $cache = [];
		if ( array_key_exists( $name, $cache ) ) {
			return $cache[$name];
		}
		$cache[$name] = null;

		$services = MediaWikiServices::getInstance();
		$title = $services->getTitleFactory()->newFromText( $name, NS_MEDIAWIKI );
		if ( !$title ) {
			return null;
		}
		$revision = $services->getRevisionLookup()->getRevisionByTitle( $title );
		if ( !$revision ) {
			return null;
		}
		$content = $revision->getContent( 'main' );
		if ( !$content || !method_exists( $content, 'getText' ) ) {
			return null;
		}
		$text = trim( (string)$content->getText() );
		if ( $text === '' ) {
			return null;
		}
		$cache[$name] = $text;
		return $text;
	}
}
