import { reactive, computed } from 'vue';

// Work in progress

class Collection {

  constructor(collection_id, class_name) {
    this.collection_id = collection_id;
    this.class_name = class_name;

    this.state = reactive({
      collection_items: [],
    });

    this.initials = computed(() => {
      const [firstName, lastName] = this.state.name.split(' ');
      return `${firstName?.[0] || ''}${lastName?.[0] || ''}`.toUpperCase();
    });

  }

}
