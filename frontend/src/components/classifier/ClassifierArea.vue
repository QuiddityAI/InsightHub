<script setup>
import httpClient from "../../api/httpClient"

import { EllipsisVerticalIcon, TrashIcon } from "@heroicons/vue/24/outline"

import ClassifiersList from "./ClassifiersList.vue"
import ClassifierClassesList from "./ClassifierClassesList.vue"
import ClassifierClassDetails from "./ClassifierClassDetails.vue"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/settings_store"
const appState = useAppStateStore()

</script>

<script>
export default {
  inject: ["eventBus"],
  props: [],
  emits: [],
  data() {
    return {
      currently_selected_classifier: null,
      currently_selected_classifier_class: null,
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.eventBus.on('classifier_tab_is_clicked', () => {
      this.currently_selected_classifier = null
      this.currently_selected_classifier_class = null
    })
  },
  methods: {},
}
</script>

<template>
  <div>
    <ClassifiersList
      v-if="!currently_selected_classifier && !currently_selected_classifier_class"
      @classifier_selected="(classifier_id) => currently_selected_classifier = classifier_id"
      @class_selected="(class_name) => currently_selected_classifier_class = class_name">
    </ClassifiersList>

    <ClassifierClassesList
      v-if="currently_selected_classifier && !currently_selected_classifier_class"
      :classifier_id="currently_selected_classifier"
      @class_selected="(class_name) => currently_selected_classifier_class = class_name"
      @close="currently_selected_classifier = null">
    </ClassifierClassesList>

    <ClassifierClassDetails
      v-if="currently_selected_classifier && currently_selected_classifier_class"
      :classifier_id="currently_selected_classifier"
      :class_name="currently_selected_classifier_class"
      @close="currently_selected_classifier = null; currently_selected_classifier_class = null">
    </ClassifierClassDetails>
  </div>
</template>
