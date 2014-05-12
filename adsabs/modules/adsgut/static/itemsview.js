// Generated by CoffeeScript 1.7.1
(function() {
  var $, ItemView, ItemsFilterView, ItemsView, addwa, addwoa, addwoata, cdict, didupost, enval, h, parse_fqin, prefix, remIndiv, remMulti, root, time_format_iv, w,
    __bind = function(fn, me){ return function(){ return fn.apply(me, arguments); }; },
    __hasProp = {}.hasOwnProperty,
    __extends = function(child, parent) { for (var key in parent) { if (__hasProp.call(parent, key)) child[key] = parent[key]; } function ctor() { this.constructor = child; } ctor.prototype = parent.prototype; child.prototype = new ctor(); child.__super__ = parent.prototype; return child; },
    __indexOf = [].indexOf || function(item) { for (var i = 0, l = this.length; i < l; i++) { if (i in this && this[i] === item) return i; } return -1; };

  root = typeof exports !== "undefined" && exports !== null ? exports : this;

  $ = jQuery;

  h = teacup;

  w = widgets;

  prefix = GlobalVariables.ADS_PREFIX + '/adsgut';

  cdict = function(fqin, l) {
    var d;
    d = {};
    d[fqin] = l;
    return d;
  };

  parse_fqin = function(fqin) {
    var vals;
    vals = fqin.split(':');
    return vals[-1 + vals.length];
  };

  enval = function(tag) {
    var ename, title, _ref;
    ename = encodeURIComponent(tag.text);
    if (!tag.url) {
      tag.url = "" + prefix + "/postable/" + this.memberable.nick + "/group:default/filter/html?query=tagname:" + ename + "&query=tagtype:ads/tagtype:tag";
      title = (_ref = tag.title) != null ? _ref : ' data-toggle="tooltip" title="' + tag.title + {
        '"': ''
      };
      tag.id = tag.text;
      tag.pview = this.pview;
      tag.text = '<a class="tag-link" ' + title + '" href="' + tag.url + '">' + tag.text + '</a>';
      tag.by = true;
    }
    return tag;
  };

  addwa = function(tag, cback) {
    var eback;
    eback = (function(_this) {
      return function(xhr, etext) {
        return alert('Did not succeed');
      };
    })(this);
    return syncs.submit_tag(this.item.basic.fqin, this.item.basic.name, tag.id, tag.pview, cback, eback);
  };

  addwoa = function(tag, cback) {
    this.update_tags(tag.id);
    return cback();
  };

  remIndiv = function(pill) {
    var cback, eback, tag;
    tag = $(pill).attr('data-tag-id');
    if (!this.tagajaxsubmit) {
      return this.remove_from_tags(tag);
    } else {
      eback = (function(_this) {
        return function(xhr, etext) {
          return alert('Did not succeed');
        };
      })(this);
      cback = (function(_this) {
        return function(data) {};
      })(this);
      return syncs.remove_tagging(this.item.basic.fqin, tag, this.pview, cback, eback);
    }
  };

  time_format_iv = function(timestring) {
    return timestring.split('.')[0].split('T').join(" at ");
  };

  didupost = function(postings, you, fqpn) {
    var counter, p, youposted, _i, _len;
    counter = 0;
    youposted = false;
    for (_i = 0, _len = postings.length; _i < _len; _i++) {
      p = postings[_i];
      if (p[0] === fqpn) {
        counter = counter + 1;
      }
      if (p[1] === you.adsid) {
        youposted = true;
      }
    }
    if (youposted === true && counter > 1) {
      return false;
    } else if (youposted === true && counter <= 1) {
      return true;
    } else if (youposted === false) {
      return false;
    }
  };

  ItemView = (function(_super) {
    __extends(ItemView, _super);

    function ItemView() {
      this.removeItem = __bind(this.removeItem, this);
      this.removeNote = __bind(this.removeNote, this);
      this.submitNote = __bind(this.submitNote, this);
      this.update_note_ajax = __bind(this.update_note_ajax, this);
      this.addToPostsView = __bind(this.addToPostsView, this);
      this.render = __bind(this.render, this);
      this.remove_notes = __bind(this.remove_notes, this);
      this.update_notes = __bind(this.update_notes, this);
      this.update_posts = __bind(this.update_posts, this);
      this.remove_from_tags = __bind(this.remove_from_tags, this);
      this.update_tags = __bind(this.update_tags, this);
      this.update = __bind(this.update, this);
      return ItemView.__super__.constructor.apply(this, arguments);
    }

    ItemView.prototype.tagName = 'div';

    ItemView.prototype.className = 'itemcontainer';

    ItemView.prototype.events = {
      "click .notebtn": "submitNote",
      "click .removenote": "removeNote",
      "click .removeitem": "removeItem"
    };

    ItemView.prototype.initialize = function(options) {
      var _ref;
      this.submittable = options.submittable, this.counter = options.counter, this.stags = options.stags, this.notes = options.notes, this.item = options.item, this.postings = options.postings, this.memberable = options.memberable, this.noteform = options.noteform, this.tagajaxsubmit = options.tagajaxsubmit, this.suggestions = options.suggestions, this.pview = options.pview;
      this.tagsfunc = (_ref = options.tagfunc) != null ? _ref : function() {};
      this.hv = void 0;
      this.newtags = [];
      this.newnotes = [];
      this.newposts = [];
      this.therebenotes = false;
      if (this.notes.length > 0) {
        return this.therebenotes = true;
      }
    };

    ItemView.prototype.update = function(postings, notes, tags) {
      this.stags = tags;
      this.notes = notes;
      return this.postings = postings;
    };

    ItemView.prototype.update_tags = function(newtag) {
      this.newtags.push(newtag);
      return this.submittable.state = true;
    };

    ItemView.prototype.remove_from_tags = function(newtag) {
      return this.newtags = _.without(this.newtags, newtag);
    };

    ItemView.prototype.update_posts = function(newposts) {
      this.newposts = _.union(this.newposts, newposts);
      return this.submittable.state = true;
    };

    ItemView.prototype.update_notes = function(newnotetuple) {
      this.newnotes.push(newnotetuple);
      return this.submittable.state = true;
    };

    ItemView.prototype.remove_notes = function(newnotetext) {
      var ele, newernotes, _i, _len, _ref;
      newernotes = [];
      _ref = this.newnotes;
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        ele = _ref[_i];
        if (ele[0] !== newnotetext) {
          newernotes.push(ele);
        }
      }
      return this.newnotes = newernotes;
    };

    ItemView.prototype.render = function() {
      var additional, additionalpostings, adslocation, content, deleter, fqin, htmlstring, jslist, p, tagdict, thepostings, thetags, url, _ref;
      this.$el.empty();
      adslocation = GlobalVariables.ADS_ABSTRACT_BASE_URL;
      url = adslocation + ("" + this.item.basic.name);
      if (((_ref = this.pview) !== 'udg' && _ref !== 'pub' && _ref !== 'none') && didupost(this.postings, this.memberable, this.pview)) {
        deleter = '<a class="removeitem" style="cursor:pointer;"><span class="i badge badge-important">x</span></a>';
      } else {
        deleter = '';
      }
      if (this.item.whenposted) {
        htmlstring = "<div class='searchresultl'>(" + this.counter + "). <a href=\"" + url + "\">" + this.item.basic.name + "</a>&nbsp;&nbsp;(saved " + (time_format_iv(this.item.whenposted)) + ")&nbsp;&nbsp;" + deleter + "</div>";
      } else {
        htmlstring = "<div class='searchresultl'>(" + this.counter + "). <a href=\"" + url + "\">" + this.item.basic.name + "</a>&nbsp;&nbsp;" + deleter + "</div>";
      }
      fqin = this.item.basic.fqin;
      content = '';
      content = content + htmlstring;
      thetags = format_tags_for_item(fqin, cdict(fqin, this.stags), this.memberable, this.tagajaxsubmit);
      additional = "<span class='tagls'></span><br/>";
      thepostings = format_postings_for_item(fqin, cdict(fqin, (function() {
        var _i, _len, _ref1, _results;
        _ref1 = this.postings;
        _results = [];
        for (_i = 0, _len = _ref1.length; _i < _len; _i++) {
          p = _ref1[_i];
          _results.push(p[0]);
        }
        return _results;
      }).call(this)), this.memberable.nick);
      additionalpostings = "<strong>In Libraries</strong>: <span class='postls'>" + (thepostings.join(', ')) + "</span><br/>";
      additional = additional + additionalpostings;
      content = content + additional;
      this.$el.append(content);
      tagdict = {
        values: thetags,
        enhanceValue: _.bind(enval, this),
        addWithAjax: _.bind(addwa, this),
        addWithoutAjax: _.bind(addwoa, this),
        onAfterAdd: this.tagsfunc,
        ajax_submit: this.tagajaxsubmit,
        onRemove: _.bind(remIndiv, this),
        suggestions: this.suggestions,
        templates: {
          pill: '<span class="badge badge-default tag-badge" style="margin-right:3px;">{0}</span>&nbsp;&nbsp;&nbsp;&nbsp;',
          add_pill: '<span class="label label-info tag-badge" style="margin-right:3px;margin-left:7px;">add tag</span>&nbsp;',
          input_pill: '<span></span>&nbsp;',
          ok_icon: '<btn class="btn btn-primary">Apply</btn>'
        }
      };
      if (this.memberable.nick === 'anonymouse') {
        tagdict.can_add = false;
      }
      jslist = [];
      this.$('.tagls').tags(jslist, tagdict);
      this.tagsobject = jslist[0];
      if (this.noteform && this.memberable.adsid !== 'anonymouse') {
        this.hv = new w.HideableView({
          state: 0,
          widget: w.postalnote_form("make note", 2, this.pview),
          theclass: ".postalnote"
        });
        this.$el.append(this.hv.render("<strong>Notes</strong>: ").$el);
        if (this.hv.state === 0) {
          this.hv.hide();
        }
      }
      if (this.memberable.adsid === 'anonymouse' && this.therebenotes) {
        this.$el.append("<div class='anony'><span><strong>Notes</strong>:</span></div>");
      }
      if (this.therebenotes) {
        if (this.memberable.adsid === 'anonymouse') {
          this.$('.anony').append("<p class='notes'></p>");
        } else {
          this.$el.append("<p class='notes'></p>");
        }
        this.$('.notes').append(format_notes_for_item(fqin, cdict(fqin, this.notes), this.memberable.adsid, this.pview));
      }
      this.$el.append('<hr style="margin-top: 15px; margin-bottom: 10px;"/>');
      return this;
    };

    ItemView.prototype.addToPostsView = function() {
      var already, fqin, inbet, p, po, poststoshow, thepostings;
      fqin = this.item.basic.fqin;
      poststoshow = (function() {
        var _i, _len, _ref, _results;
        _ref = this.newposts;
        _results = [];
        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
          p = _ref[_i];
          if (__indexOf.call((function() {
            var _j, _len1, _ref1, _results1;
            _ref1 = this.postings;
            _results1 = [];
            for (_j = 0, _len1 = _ref1.length; _j < _len1; _j++) {
              po = _ref1[_j];
              _results1.push(po[0]);
            }
            return _results1;
          }).call(this), p) < 0) {
            _results.push(p);
          }
        }
        return _results;
      }).call(this);
      thepostings = format_postings_for_item(fqin, cdict(fqin, poststoshow), this.memberable.nick);
      already = format_postings_for_item(fqin, cdict(fqin, (function() {
        var _i, _len, _ref, _results;
        _ref = this.postings;
        _results = [];
        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
          p = _ref[_i];
          _results.push(p[0]);
        }
        return _results;
      }).call(this)), this.memberable.nick).join(', ');
      inbet = '';
      if (already !== '') {
        inbet = ', ';
      }
      return this.$('.postls').html(already + inbet + thepostings.join(', '));
    };

    ItemView.prototype.update_note_ajax = function(data) {
      var fqin, notes, stags, _ref;
      fqin = this.item.basic.fqin;
      _ref = get_taggings(data), stags = _ref[0], notes = _ref[1];
      this.stags = stags[fqin];
      this.notes = notes[fqin];
      if (this.notes.length > 0) {
        this.therebenotes = true;
      }
      return this.render();
    };

    ItemView.prototype.submitNote = function() {
      var cback, ctxt, d, eback, item, itemname, loc, notemode, notetext, notetime;
      item = this.item.basic.fqin;
      itemname = this.item.basic.name;
      notetext = this.$('.txt').val();
      notemode = '1';
      if (this.$('.cb').is(':checked')) {
        if (this.pview === 'pub') {
          notemode = '0';
        } else if (this.pview === 'udg' || this.pview === 'none') {
          notemode = '0';
        } else {
          notemode = this.pview;
        }
      }
      ctxt = this.pview;
      loc = window.location;
      cback = (function(_this) {
        return function(data) {
          _this.update_note_ajax(data);
          return format_item(_this.$('.searchresultl'), _this.e);
        };
      })(this);
      eback = (function(_this) {
        return function(xhr, etext) {
          return alert('Did not succeed');
        };
      })(this);
      if (this.tagajaxsubmit) {
        syncs.submit_note(item, itemname, [notetext, notemode], ctxt, cback, eback);
      } else {
        this.update_notes([notetext, notemode]);
        if (!this.therebenotes) {
          this.$el.append("<p class='notes'></p>");
          this.$(".notes").append("<table class='table-condensed table-striped'></table>");
          this.therebenotes = true;
        }
        d = new Date();
        notetime = d.toISOString();
        this.$('.notes table').prepend(format_row("randomid", notetext, notemode, notetime, this.memberable, this.memberable, false, this.pview));
        this.hv.hide();
        this.$('.txt').val("");
        this.submittable.state = true;
      }
      return false;
    };

    ItemView.prototype.removeNote = function(e) {
      var $target, cback, eback, item, itemname, notetext, tagname;
      item = this.item.basic.fqin;
      itemname = this.item.basic.name;
      $target = $(e.currentTarget);
      cback = (function(_this) {
        return function(data) {
          _this.update_note_ajax(data);
          return format_item(_this.$('.searchresultl'), _this.e);
        };
      })(this);
      eback = (function(_this) {
        return function(xhr, etext) {
          return alert('Did not succeed');
        };
      })(this);
      if (this.tagajaxsubmit) {
        tagname = $target.attr('id');
        syncs.remove_note(item, tagname, this.pview, cback, eback);
      } else {
        notetext = $target.parents("tr").find("td.notetext").text();
        this.remove_notes(notetext);
        $target.parents("tr").remove();
      }
      return false;
    };

    ItemView.prototype.removeItem = function() {
      var cback, eback, item, itemname;
      item = this.item.basic.fqin;
      itemname = this.item.basic.name;
      cback = (function(_this) {
        return function(data) {
          var ix, nump;
          _this.remove();
          nump = $('#count').text();
          ix = nump.search('papers');
          nump = Number(nump.slice(0, ix)) - 1;
          return $('#count').text("" + nump + " papers. ");
        };
      })(this);
      eback = (function(_this) {
        return function(xhr, etext) {
          return alert('Did not succeed');
        };
      })(this);
      if (this.tagajaxsubmit) {
        syncs.remove_items_from_postable([item], this.pview, cback, eback);
      }
      return false;
    };

    return ItemView;

  })(Backbone.View);

  addwoata = function(tag, cback) {
    this.update_tags(tag);
    return cback();
  };

  remMulti = function(pill) {
    var fqin, i, tag, _i, _len, _ref, _results;
    tag = $(pill).attr('data-tag-id');
    if (!this.tagajaxsubmit) {
      _ref = this.items;
      _results = [];
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        i = _ref[_i];
        fqin = i.basic.fqin;
        _results.push(this.itemviews[fqin].tagsobject.removeTag(this.itemviews[fqin].$("[data-tag-id='" + tag + "']")));
      }
      return _results;
    } else {

    }
  };

  ItemsView = (function(_super) {
    __extends(ItemsView, _super);

    function ItemsView() {
      this.submitTags = __bind(this.submitTags, this);
      this.collectPosts = __bind(this.collectPosts, this);
      this.collectNotes = __bind(this.collectNotes, this);
      this.collectTags = __bind(this.collectTags, this);
      this.submitPosts = __bind(this.submitPosts, this);
      this.iDone = __bind(this.iDone, this);
      this.iCancel = __bind(this.iCancel, this);
      this.subNewLib = __bind(this.subNewLib, this);
      this.render = __bind(this.render, this);
      this.update_posts = __bind(this.update_posts, this);
      this.update_tags = __bind(this.update_tags, this);
      this.update_postings_taggings = __bind(this.update_postings_taggings, this);
      return ItemsView.__super__.constructor.apply(this, arguments);
    }

    ItemsView.prototype.events = {
      "click .post": "submitPosts",
      "click .tag": "submitTags",
      "click .done": "iDone",
      "click .cancel": "iCancel",
      "click .libsub": "subNewLib"
    };

    ItemsView.prototype.initialize = function(options) {
      this.stags = options.stags, this.notes = options.notes, this.$el = options.$el, this.postings = options.postings, this.memberable = options.memberable, this.items = options.items, this.nameable = options.nameable, this.itemtype = options.itemtype, this.loc = options.loc, this.noteform = options.noteform, this.suggestions = options.suggestions, this.pview = options.pview;
      this.newposts = [];
      this.tagajaxsubmit = false;
      return this.submittable = {
        state: false
      };
    };

    ItemsView.prototype.update_postings_taggings = function() {
      var i, itemlist, itemsq;
      this.postings = {};
      itemlist = (function() {
        var _i, _len, _ref, _results;
        _ref = this.items;
        _results = [];
        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
          i = _ref[_i];
          _results.push("items=" + (encodeURIComponent(i.basic.fqin)));
        }
        return _results;
      }).call(this);
      itemsq = itemlist.join("&");
      return $.get(prefix + ("/items/taggingsandpostings?" + itemsq), (function(_this) {
        return function(data) {
          var e, fqin, k, v, _i, _len, _ref, _ref1, _ref2, _results;
          _ref = get_taggings(data), _this.stags = _ref[0], _this.notes = _ref[1];
          _ref1 = data.postings;
          for (k in _ref1) {
            if (!__hasProp.call(_ref1, k)) continue;
            v = _ref1[k];
            if (v[0] > 0) {
              _this.postings[k] = (function() {
                var _i, _len, _ref2, _results;
                _ref2 = v[1];
                _results = [];
                for (_i = 0, _len = _ref2.length; _i < _len; _i++) {
                  e = _ref2[_i];
                  _results.push(e.posting.postfqin);
                }
                return _results;
              })();
            } else {
              _this.postings[k] = [];
            }
          }
          _ref2 = _this.items;
          _results = [];
          for (_i = 0, _len = _ref2.length; _i < _len; _i++) {
            i = _ref2[_i];
            fqin = i.basic.fqin;
            _this.itemviews[fqin].update(_this.postings[fqin], _this.notes[fqin], _this.stags[fqin]);
            _results.push(_this.itemviews[fqin].render());
          }
          return _results;
        };
      })(this));
    };

    ItemsView.prototype.update_tags = function(newtag) {
      var fqin, i, _i, _len, _ref;
      _ref = this.items;
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        i = _ref[_i];
        fqin = i.basic.fqin;
        this.itemviews[fqin].tagsobject.addTag(this.itemviews[fqin].$('.pills-list'), newtag);
      }
      return this.submittable.state = true;
    };

    ItemsView.prototype.update_posts = function(postables) {
      var fqin, i, p, _i, _j, _len, _len1, _ref;
      for (_i = 0, _len = postables.length; _i < _len; _i++) {
        p = postables[_i];
        this.newposts = _.union(this.newposts, postables);
      }
      _ref = this.items;
      for (_j = 0, _len1 = _ref.length; _j < _len1; _j++) {
        i = _ref[_j];
        fqin = i.basic.fqin;
        this.itemviews[fqin].update_posts(this.newposts);
        this.itemviews[fqin].addToPostsView();
      }
      return this.submittable.state = true;
    };

    ItemsView.prototype.render = function() {
      var $ctrls, $lister, cback, counter, eback, fqin, i, ins, v, _i, _len, _ref;
      $lister = this.$('.items');
      $ctrls = this.$('.ctrls');
      this.itemviews = {};
      counter = 1;
      _ref = this.items;
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        i = _ref[_i];
        fqin = i.basic.fqin;
        ins = {
          stags: this.stags[fqin],
          notes: this.notes[fqin],
          postings: this.postings[fqin],
          item: i,
          memberable: this.memberable,
          noteform: this.noteform,
          tagajaxsubmit: this.tagajaxsubmit,
          suggestions: this.suggestions,
          pview: this.pview,
          counter: counter,
          submittable: this.submittable
        };
        v = new ItemView(ins);
        $lister.append(v.render().el);
        $lister.append('<hr style="margin-top: 10px; margin-bottom: 10px;"/>');
        this.itemviews[fqin] = v;
        counter = counter + 1;
      }
      eback = (function(_this) {
        return function(xhr, etext) {
          return alert('Did not succeed');
        };
      })(this);
      cback = (function(_this) {
        return function(data) {
          var jslist, libs, tagdict;
          libs = _.union(data.libraries, data.groups).sort();
          $ctrls.append(w.postalall_form(_this.nameable, _this.itemtype, libs));
          tagdict = {
            enhanceValue: _.bind(enval, _this),
            addWithAjax: _.bind(addwa, _this),
            addWithoutAjax: _.bind(addwoata, _this),
            ajax_submit: false,
            onRemove: _.bind(remMulti, _this),
            suggestions: _this.suggestions,
            templates: {
              pill: '<span class="badge badge-default tag-badge" style="margin-right:3px;">{0}</span>&nbsp;&nbsp;&nbsp;&nbsp;',
              add_pill: '<span class="label label-info tag-badge" style="margin-right:3px;margin-left:7px;">add tag</span>&nbsp;',
              input_pill: '<span></span>&nbsp;',
              ok_icon: '<btn class="btn btn-primary">Apply</btn>'
            }
          };
          jslist = [];
          _this.$('#alltags').tags(jslist, tagdict);
          _this.$('.multilibrary').multiselect({
            includeSelectAllOption: true,
            maxHeight: 150
          });
          return _this.globaltagsobject = jslist[0];
        };
      })(this);
      syncs.get_postables_writable(this.memberable.nick, cback, eback);
      return this;
    };

    ItemsView.prototype.subNewLib = function() {
      var cback, cback2, eback, postable, postabletype;
      postable = {
        name: this.$('.libtxt').val(),
        description: ''
      };
      postabletype = "library";
      this.$('.libtxt').empty();
      eback = (function(_this) {
        return function(xhr, etext) {
          return alert('Did not succeed');
        };
      })(this);
      cback2 = (function(_this) {
        return function(data) {
          var c, librarychoicedict, libs, value, _i, _len;
          libs = _.union(data.libraries, data.groups);
          librarychoicedict = {};
          for (_i = 0, _len = libs.length; _i < _len; _i++) {
            c = libs[_i];
            librarychoicedict[c] = parse_fqin(c);
            if (postable.name === librarychoicedict[c]) {
              value = c;
            }
          }
          _this.$('.posthorizontal').empty();
          _this.$('.posthorizontal').append(w.postcontrol(libs, librarychoicedict));
          _this.$('.multilibrary').multiselect({
            includeSelectAllOption: true,
            maxHeight: 150
          });
          if (value) {
            return _this.$('.multilibrary').multiselect('select', value);
          }
        };
      })(this);
      cback = (function(_this) {
        return function(data) {
          return syncs.get_postables_writable(_this.memberable.nick, cback2, eback);
        };
      })(this);
      return syncs.create_postable(postable, postabletype, cback, eback);
    };

    ItemsView.prototype.iCancel = function() {
      return $.fancybox.close();
    };

    ItemsView.prototype.iDone = function() {
      var cback, cback_notes, cback_posts, cback_tags, eback, ns, postables, ts;
      cback = (function(_this) {
        return function(data) {
          return $.fancybox.close();
        };
      })(this);
      eback = (function(_this) {
        return function(xhr, etext) {
          return alert('Did not succeed');
        };
      })(this);
      postables = this.collectPosts();
      ts = this.collectTags();
      ns = this.collectNotes();
      cback_notes = (function(_this) {
        return function() {
          return syncs.submit_notes(_this.items, ns, cback, eback);
        };
      })(this);
      cback_tags = (function(_this) {
        return function() {
          return syncs.submit_tags(_this.items, ts, postables, cback_notes, eback);
        };
      })(this);
      cback_posts = (function(_this) {
        return function() {
          return syncs.submit_posts(_this.items, postables, cback_tags, eback);
        };
      })(this);
      syncs.save_items(this.items, cback_posts, eback);
      return false;
    };

    ItemsView.prototype.submitPosts = function() {
      var cback, eback, libs, loc, postables;
      libs = this.$('.multilibrary').val();
      if (libs === null) {
        libs = [];
      }
      postables = _.without(libs, 'multiselect-all');
      $('option', this.$('.multilibrary')).each(function(ele) {
        return $(this).removeAttr('selected').prop('selected', false);
      });
      this.$('.multilibrary').multiselect('refresh');
      loc = window.location;
      cback = (function(_this) {
        return function(data) {
          return _this.update_postings_taggings();
        };
      })(this);
      eback = (function(_this) {
        return function(xhr, etext) {
          return alert('Did not succeed saving to libraries');
        };
      })(this);
      if (this.tagajaxsubmit) {
        syncs.submit_posts(this.items, postables, cback, eback);
      } else {
        this.update_posts(postables);
      }
      return false;
    };

    ItemsView.prototype.collectTags = function() {
      var e, fqin, i, iview, ntags, tags, _i, _len, _ref;
      tags = {};
      _ref = this.items;
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        i = _ref[_i];
        fqin = i.basic.fqin;
        iview = this.itemviews[fqin];
        ntags = iview.newtags;
        tags[fqin] = (function() {
          var _j, _len1, _results;
          _results = [];
          for (_j = 0, _len1 = ntags.length; _j < _len1; _j++) {
            e = ntags[_j];
            if (e !== "") {
              _results.push(e.trim());
            }
          }
          return _results;
        })();
      }
      return tags;
    };

    ItemsView.prototype.collectNotes = function() {
      var e, fqin, i, iview, notes, ntags, _i, _len, _ref;
      notes = {};
      _ref = this.items;
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        i = _ref[_i];
        fqin = i.basic.fqin;
        iview = this.itemviews[fqin];
        if (iview.therebenotes) {
          ntags = iview.newnotes;
        } else {
          ntags = [];
        }
        notes[fqin] = (function() {
          var _j, _len1, _results;
          _results = [];
          for (_j = 0, _len1 = ntags.length; _j < _len1; _j++) {
            e = ntags[_j];
            if (e[0] !== "") {
              _results.push([e[0].trim(), e[1]]);
            }
          }
          return _results;
        })();
      }
      return notes;
    };

    ItemsView.prototype.collectPosts = function() {
      return this.newposts;
    };

    ItemsView.prototype.submitTags = function() {
      var cback, e, eback, fqin, i, loc, tags, tagstring, ts, _i, _len, _ref;
      ts = {};
      tagstring = this.$('.tagsinput').val();
      if (tagstring === "") {
        tags = [];
      } else {
        tags = (function() {
          var _i, _len, _ref, _results;
          _ref = tagstring.split(',');
          _results = [];
          for (_i = 0, _len = _ref.length; _i < _len; _i++) {
            e = _ref[_i];
            _results.push(e.trim());
          }
          return _results;
        })();
        tags = (function() {
          var _i, _len, _results;
          _results = [];
          for (_i = 0, _len = tags.length; _i < _len; _i++) {
            e = tags[_i];
            if (e !== "") {
              _results.push(e);
            }
          }
          return _results;
        })();
      }
      loc = window.location;
      _ref = this.items;
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        i = _ref[_i];
        fqin = i.basic.fqin;
        ts[fqin] = tags;
      }
      cback = (function(_this) {
        return function(data) {
          return _this.update_postings_taggings();
        };
      })(this);
      eback = (function(_this) {
        return function(xhr, etext) {
          return alert('Did not succeed tagging');
        };
      })(this);
      syncs.submit_tags(this.items, ts, cback, eback);
      return false;
    };

    return ItemsView;

  })(Backbone.View);

  ItemsFilterView = (function(_super) {
    __extends(ItemsFilterView, _super);

    function ItemsFilterView() {
      this.render = __bind(this.render, this);
      return ItemsFilterView.__super__.constructor.apply(this, arguments);
    }

    ItemsFilterView.prototype.initialize = function(options) {
      this.stags = options.stags, this.notes = options.notes, this.$el = options.$el, this.postings = options.postings, this.memberable = options.memberable, this.items = options.items, this.nameable = options.nameable, this.itemtype = options.itemtype, this.noteform = options.noteform, this.suggestions = options.suggestions, this.pview = options.pview, this.tagfunc = options.tagfunc;
      return this.submittable = {
        state: true
      };
    };

    ItemsFilterView.prototype.render = function() {
      var counter, fqin, i, ins, v, _i, _len, _ref;
      this.itemviews = {};
      counter = 1;
      _ref = this.items;
      for (_i = 0, _len = _ref.length; _i < _len; _i++) {
        i = _ref[_i];
        fqin = i.basic.fqin;
        ins = {
          stags: this.stags[fqin],
          notes: this.notes[fqin],
          postings: this.postings[fqin],
          item: i,
          memberable: this.memberable,
          noteform: this.noteform,
          tagajaxsubmit: true,
          suggestions: this.suggestions,
          pview: this.pview,
          tagfunc: this.tagfunc,
          counter: counter,
          submittable: this.submittable
        };
        v = new ItemView(ins);
        this.$el.append(v.render().el);
        this.itemviews[fqin] = v;
        counter = counter + 1;
      }
      return this;
    };

    return ItemsFilterView;

  })(Backbone.View);

  root.itemsdo = {
    ItemView: ItemView,
    ItemsView: ItemsView,
    ItemsFilterView: ItemsFilterView
  };

}).call(this);
