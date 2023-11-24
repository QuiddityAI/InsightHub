<script setup>
import httpClient from '../api/httpClient';

import { EllipsisVerticalIcon, TrashIcon, BookOpenIcon } from '@heroicons/vue/24/outline'

import ClassifierExample from './ClassifierExample.vue';
import { mapStores } from 'pinia'
import { useAppStateStore } from '../stores/settings_store'
import { FieldType } from '../utils/utils';

const appState = useAppStateStore()
</script>

<script>
export default {
  props: ["classifier", "class_name"],
  emits: ["delete_classifier", "recommend_items_for_classifier", "show_classifier_as_map"],
  data() {
    return {
      settings_visible: false,
      examples_visible: false,
      examples: [],
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  mounted() {
  },
  watch: {
    examples_visible: function (new_val, old_val) {
      if (this.examples_visible) {
        this.load_examples()
      }
    },
  },
  methods: {
    load_examples() {
      const that = this
      const body = {
        classifier_id: this.classifier.id,
        class_name: this.class_name,
        type: FieldType.IDENTIFIER,
      }
      httpClient.post("/org/data_map/get_classifier_examples", body)
        .then(function (response) {
          that.examples = response.data
        })
    },
    remove_item_from_classifier(item_id, is_positive) {
      const that = this
      const body = {
        classifier_id: this.classifier.id,
        item_id: item_id,
        is_positive: is_positive,
      }
      httpClient.post("/org/data_map/remove_item_from_classifier", body)
        .then(function (response) {
          // 'classifier' prop is read-only, so get writable reference:
          const classifier_index = that.appStateStore.classifiers.findIndex((col) => col.id === that.classifier.id)
          const classifier = that.appStateStore.classifiers[classifier_index]

          if (is_positive) {
            const item_index = classifier.positive_ids.indexOf(item_id)
            classifier.positive_ids.splice(item_index, 1)
          } else {
            const item_index = classifier.negative_ids.indexOf(item_id)
            classifier.negative_ids.splice(item_index, 1)
          }
        })
    },
  },
}
</script>

<!-- TODO: add button to train concept, add threshold settings, add checkbox to mark results in map, add color / symbol select box,
  collaps list etc. -->

<template>

<li>
  <div class="flex flex-row gap-3">
    <span class="ml-3 text-gray-500">{{ class_name == '_default' ? 'Items' : class_name }}</span>
    <div class="flex-1"></div>
    <button @click="$emit('recommend_items_for_classifier', classifier)" class="text-sm text-gray-500 font-light hover:text-blue-500/50">Recommend Similar</button>
    <button @click="$emit('show_classifier_as_map', classifier)" class="text-sm text-gray-500 font-light hover:text-blue-500/50">Show Map</button>
    <button @click="settings_visible = !settings_visible" class="w-8 px-1 ml-1 hover:bg-gray-100 rounded" :class="{ 'text-blue-600': settings_visible, 'text-gray-500': !settings_visible }">
      <EllipsisVerticalIcon></EllipsisVerticalIcon>
    </button>
    <button @click="examples_visible = !examples_visible" class="w-8 px-1 ml-1 hover:bg-gray-100 rounded" :class="{ 'text-blue-600': examples_visible, 'text-gray-500': !examples_visible }">
      <BookOpenIcon></BookOpenIcon>
    </button>
  </div>
  <div v-if="settings_visible" class="flex flex-row gap-3 mt-2">
    <button @click="train_classifier" class="text-sm text-gray-500 font-light hover:text-blue-500/50">Train Classifier</button>
    <button @click="" class="text-sm text-gray-500 font-light hover:text-blue-500/50">X: highlight similar in map</button>
    <button @click="" class="text-sm text-gray-500 font-light hover:text-blue-500/50">Color: xxx</button>
    <button @click="" class="text-sm text-gray-500 font-light hover:text-blue-500/50">Symbol: xxx</button>
    <div class="flex-1"></div>
    <button @click="$emit('delete_classifier', classifier.id)" class="w-6 px-1 ml-1 hover:bg-red-100 rounded text-gray-500">
      <TrashIcon></TrashIcon>
    </button>
  </div>

  <ul v-if="examples_visible" class="pt-2">
    <li v-for="example in examples" :key="example.id" class="justify-between pb-2">
      <ClassifierExample :item_id="example.value" :is_positive="example.is_positive"
        @remove="remove_item_from_classifier(example.id, true)">
      </ClassifierExample>
    </li>
  </ul>
</li>

</template>


<style scoped></style>
