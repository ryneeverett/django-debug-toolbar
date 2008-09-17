jQuery.noConflict();
(function(jQuery) {
	jQuery.djDebug = function(data, klass) {
		jQuery.djDebug.init();
	}
	jQuery.extend(jQuery.djDebug, {
		init: function() {
			var current = null;
			jQuery('#djDebugPanelList li a').click(function() {
				current = jQuery('#djDebug #' + this.className);
				if (current.is(':visible')) {
					jQuery(document).trigger('close.djDebug');
				} else {
					jQuery('.panelContent').hide();
					current.show();
					jQuery.djDebug.open();
				}
				return false;
			});
			jQuery('#djDebug a.close').click(function() {
				jQuery(document).trigger('close.djDebug');
				return false;
			});
		},
		open: function() {
			jQuery(document).bind('keydown.djDebug', function(e) {
				if (e.keyCode == 27) {
					jQuery.djDebug.close();
				}
			});
		},
		close: function() {
			jQuery(document).trigger('close.djDebug');
			return false;
		}
	});
	jQuery(document).bind('close.djDebug', function() {
		jQuery(document).unbind('keydown.djDebug');
		jQuery('.panelContent').hide();
	});
})(jQuery);
jQuery(document).ready(function() {
	jQuery.djDebug();
});
