var script = document.createElement('script');
script.src = 'https://code.jquery.com/jquery-3.6.3.min.js';
document.getElementsByTagName('head')[0].appendChild(script);


$(function() {

  function hide_parameters_based_on_field_type(object_field_id, field_type) {
    const parameter_to_field_types = {
      index_parameters: ['VECTOR',],
      language_analysis: ['TEXT', 'STRING',],
      embedding_space: ['VECTOR',],
      text_similarity_threshold: ['VECTOR',],
      image_similarity_threshold: ['VECTOR',],
      action_buttons: ['VECTOR',],
    }
    for (const [parameter, field_types] of Object.entries(parameter_to_field_types)) {
      const parameter_field = $(`#object_fields-${object_field_id} .field-${parameter}`)
      field_types.includes(field_type) ? parameter_field.show() : parameter_field.hide()
    }
  }

  function hide_parameters_based_generator_being_set(object_field_id, has_generator) {
    const parameters_to_show_for_generator = [
      'generator_parameters',
      'generating_condition',
      'source_fields',
      'should_be_generated',
    ]
    for (const parameter of parameters_to_show_for_generator) {
      const parameter_field = $(`#object_fields-${object_field_id} .field-${parameter}`)
      has_generator ? parameter_field.show() : parameter_field.hide()
    }
  }

  function assign_listeners() {
    for (const object_field_id of Array(100).keys()) {
      const select_field = $(`#id_object_fields-${object_field_id}-field_type`)
      if (!select_field.length) {
        break
      }

      hide_parameters_based_on_field_type(object_field_id, select_field.val())

      select_field.change(function() {
        hide_parameters_based_on_field_type(object_field_id, $(this).val());
      })

      const generator_select_field = $(`#id_object_fields-${object_field_id}-generator`)

      hide_parameters_based_generator_being_set(object_field_id, generator_select_field.val() !== '')
      generator_select_field.change(function() {
        hide_parameters_based_generator_being_set(object_field_id, $(this).val() !== '');
      })
    }
  }
  assign_listeners()

  var observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.addedNodes && mutation.addedNodes.length > 0) {
            // element added to DOM
            var hasClass = [].some.call(mutation.addedNodes, function(el) {
                return el.classList ? el.classList.contains('dynamic-object_fields') : false
            });
            if (hasClass) {
                // element has class `dynamic-object_fields`
                assign_listeners()
            }
        }
    });
  });

  var config = {
      attributes: true,
      childList: true,
      characterData: true,
      subtree: true
  };

  observer.observe(document.body, config);
});
